use codex_history::ResponseItemEnvelope;
use codex_protocol::models::ContentItem;
use codex_protocol::models::FunctionCallOutputContentItem;
use codex_protocol::models::FunctionCallOutputPayload;
use codex_protocol::models::ResponseItem;

/// Placeholder inserted only into an outbound request copy when a tool call must be
/// transported without its matching output item. Durable history keeps the real
/// output; the provider receives a paired, text-only stand-in instead of a broken
/// request shape.
const OMITTED_TOOL_OUTPUT_PLACEHOLDER: &str = "[tool output omitted before transport by the local client; \
the original output is present in local task history]";

const IMAGE_RESIZE_NOTICE_START: &str = "<image_resize_notice>";
const IMAGE_RESIZE_NOTICE_END: &str = "</image_resize_notice>";

/// A prompt-copy item. Both the plain response item and the annotated history
/// envelope can be normalized without touching persisted rollout data.
trait PromptCopyItem: Sized {
    fn response_item(&self) -> &ResponseItem;
    fn response_item_mut(&mut self) -> &mut ResponseItem;
}
impl PromptCopyItem for ResponseItem {
    fn response_item(&self) -> &ResponseItem {
        self
    }

    fn response_item_mut(&mut self) -> &mut ResponseItem {
        self
    }
}

impl PromptCopyItem for ResponseItemEnvelope {
    fn response_item(&self) -> &ResponseItem {
        &self.item
    }

    fn response_item_mut(&mut self) -> &mut ResponseItem {
        &mut self.item
    }
}

/// Filters and normalizes only an outbound request copy. Rollout history is never modified.
pub(crate) fn sanitize_prompt_history(
    target_provider_id: &str,
    items: Vec<ResponseItem>,
) -> Vec<ResponseItem> {
    sanitize_items(target_provider_id, items)
}

pub(crate) fn sanitize_prompt_history_annotated(
    target_provider_id: &str,
    items: Vec<ResponseItemEnvelope>,
) -> Vec<ResponseItemEnvelope> {
    sanitize_items(target_provider_id, items)
}

fn sanitize_items<T>(target_provider_id: &str, items: Vec<T>) -> Vec<T>
where
    T: PromptCopyItem + From<ResponseItem>,
{
    let target_is_openai = target_provider_id.eq_ignore_ascii_case("openai");
    let mut removed = 0usize;
    let filtered = items
        .into_iter()
        .filter(|item| {
            let keep = match item.response_item() {
                ResponseItem::Reasoning {
                    content,
                    encrypted_content,
                    ..
                } => {
                    let has_plaintext = content.as_ref().is_some_and(|value| !value.is_empty());
                    let has_encrypted = encrypted_content
                        .as_ref()
                        .is_some_and(|value| !value.is_empty());
                    if target_is_openai {
                        !has_plaintext && has_encrypted
                    } else {
                        has_plaintext
                    }
                }
                _ => true,
            };
            if !keep {
                removed = removed.saturating_add(1);
            }
            keep
        })
        .collect::<Vec<T>>();
    if removed > 0 {
        tracing::info!(
            target_provider_id,
            removed,
            "removed provider-incompatible reasoning items from prompt copy"
        );
    }
    if target_is_openai {
        return filtered;
    }

    let (items, merged_notices) = merge_image_resize_notices(filtered);
    let (items, relocated_messages) = relocate_messages_away_from_tool_outputs(items);
    let (items, inserted_outputs, removed_outputs) = repair_tool_call_pairing(items);
    if merged_notices + relocated_messages + inserted_outputs + removed_outputs > 0 {
        tracing::info!(
            target_provider_id,
            merged_notices,
            relocated_messages,
            inserted_outputs,
            removed_outputs,
            "normalized provider-incompatible tool-call shapes in prompt copy"
        );
    }
    items
}

/// Client-authored image resize notices are derived from the item they follow.
/// Providers that fail to associate a tool output with the item after a message
/// (DeepSeek's Responses endpoint is one) need the notice folded back into that
/// item's content instead of travelling as a standalone message.
fn merge_image_resize_notices<T>(items: Vec<T>) -> (Vec<T>, usize)
where
    T: PromptCopyItem,
{
    let mut merged = 0usize;
    let mut output: Vec<T> = Vec::with_capacity(items.len());
    for item in items {
        let notice = image_resize_notice_text(item.response_item()).map(str::to_owned);
        if let Some(notice) = notice {
            let folded = output
                .last_mut()
                .is_some_and(|previous| append_text_content(previous.response_item_mut(), &notice));
            if folded {
                merged = merged.saturating_add(1);
                continue;
            }
        }
        output.push(item);
    }
    (output, merged)
}

fn image_resize_notice_text(item: &ResponseItem) -> Option<&str> {
    let ResponseItem::Message { role, content, .. } = item else {
        return None;
    };
    if role != "developer" {
        return None;
    }
    let mut text = None;
    for part in content {
        let ContentItem::InputText { text: part_text } = part else {
            return None;
        };
        let Some(existing) = text.as_mut() else {
            text = Some(part_text.as_str());
            continue;
        };
        if existing.len() < part_text.len() {
            *existing = part_text.as_str();
        }
    }
    let text = text?;
    (text.contains(IMAGE_RESIZE_NOTICE_START) && text.contains(IMAGE_RESIZE_NOTICE_END))
        .then_some(text)
}

fn append_text_content(item: &mut ResponseItem, text: &str) -> bool {
    match item {
        ResponseItem::Message { content, .. } => {
            content.push(ContentItem::InputText {
                text: text.to_owned(),
            });
            true
        }
        ResponseItem::FunctionCallOutput { output, .. }
        | ResponseItem::CustomToolCallOutput { output, .. } => {
            if let Some(existing) = output.text_content().map(str::to_owned) {
                *output = FunctionCallOutputPayload::from_content_items(vec![
                    FunctionCallOutputContentItem::InputText { text: existing },
                    FunctionCallOutputContentItem::InputText {
                        text: text.to_owned(),
                    },
                ]);
                return true;
            }
            match output.content_items_mut() {
                Some(content) => {
                    content.push(FunctionCallOutputContentItem::InputText {
                        text: text.to_owned(),
                    });
                    true
                }
                None => false,
            }
        }
        _ => false,
    }
}

/// Some Responses-compatible providers only associate a tool output when no
/// message item sits directly in front of it. Only a message run that
/// interrupts the call/output region moves: a run whose predecessor is a tool
/// call (call -> message -> output) or another tool output (output -> message
/// -> output). Message runs that precede the whole batch (history, developer
/// instructions, the assistant turn text) stay where they are; moving those
/// was proven to break the provider's call association on real payloads.
fn relocate_messages_away_from_tool_outputs<T>(items: Vec<T>) -> (Vec<T>, usize)
where
    T: PromptCopyItem,
{
    enum Action {
        Buffer,
        FlushPendingThenKeep,
        Keep,
    }

    let mut relocated = 0usize;
    let mut output: Vec<T> = Vec::with_capacity(items.len());
    let mut pending: Vec<T> = Vec::new();
    for item in items {
        let action = match item.response_item() {
            ResponseItem::Message { .. } => Action::Buffer,
            current if is_tool_output(current) => Action::FlushPendingThenKeep,
            _ => Action::Keep,
        };
        match action {
            Action::Buffer => {
                pending.push(item);
            }
            Action::FlushPendingThenKeep => {
                let interrupts_call_pair = !pending.is_empty()
                    && output
                        .last()
                        .is_some_and(|previous| is_call_family(previous.response_item()));
                let interrupts_output_pair = !pending.is_empty()
                    && output
                        .last()
                        .is_some_and(|previous| is_tool_output(previous.response_item()));
                if interrupts_call_pair || interrupts_output_pair {
                    let insert_at = output
                        .iter()
                        .rposition(|existing| is_call_family(existing.response_item()))
                        .unwrap_or(output.len());
                    for message in pending.drain(..).rev() {
                        output.insert(insert_at, message);
                    }
                    relocated = relocated.saturating_add(1);
                } else {
                    output.append(&mut pending);
                }
                output.push(item);
            }
            Action::Keep => {
                // A message run only ever moves when it interrupts a call and
                // its output. Anything else (reasoning text, the assistant
                // turn, the next call) closes the run in place.
                output.append(&mut pending);
                output.push(item);
            }
        }
    }
    for message in pending {
        output.push(message);
    }
    (output, relocated)
}

/// A provider rejects a request whose tool call has no output (and one whose
/// output has no call). Keep the copy transportable: synthesize a text-only
/// output for a dangling call and drop an output whose call is gone.
fn repair_tool_call_pairing<T>(items: Vec<T>) -> (Vec<T>, usize, usize)
where
    T: PromptCopyItem + From<ResponseItem>,
{
    let mut call_ids = std::collections::HashSet::new();
    let mut output_ids = std::collections::HashSet::new();
    for item in &items {
        match item.response_item() {
            ResponseItem::FunctionCall { call_id, .. }
            | ResponseItem::CustomToolCall { call_id, .. } => {
                call_ids.insert(call_id.clone());
            }
            ResponseItem::FunctionCallOutput { call_id, .. } => {
                if let Some(call_id) = call_id {
                    output_ids.insert(call_id.clone());
                }
            }
            ResponseItem::CustomToolCallOutput { call_id, .. } => {
                output_ids.insert(call_id.clone());
            }
            _ => {}
        }
    }

    let mut inserted = 0usize;
    let mut removed = 0usize;
    let mut repaired: Vec<T> = Vec::with_capacity(items.len());
    for item in items {
        let (keep, stand_in) = match item.response_item() {
            current if is_tool_output(current) => {
                let known = match current {
                    ResponseItem::FunctionCallOutput { call_id, .. } => call_id
                        .as_ref()
                        .is_some_and(|call_id| call_ids.contains(call_id)),
                    ResponseItem::CustomToolCallOutput { call_id, .. } => {
                        call_ids.contains(call_id)
                    }
                    _ => true,
                };
                (known, None)
            }
            ResponseItem::FunctionCall {
                call_id,
                name,
                namespace,
                ..
            } if !output_ids.contains(call_id) => (
                true,
                Some(ResponseItem::FunctionCallOutput {
                    id: None,
                    call_id: Some(call_id.clone()),
                    name: Some(name.clone()),
                    namespace: namespace.clone(),
                    output: FunctionCallOutputPayload::from_text(
                        OMITTED_TOOL_OUTPUT_PLACEHOLDER.to_owned(),
                    ),
                    internal_chat_message_metadata_passthrough: None,
                }),
            ),
            ResponseItem::CustomToolCall { call_id, name, .. } if !output_ids.contains(call_id) => {
                (
                    true,
                    Some(ResponseItem::CustomToolCallOutput {
                        id: None,
                        call_id: call_id.clone(),
                        name: Some(name.clone()),
                        output: FunctionCallOutputPayload::from_text(
                            OMITTED_TOOL_OUTPUT_PLACEHOLDER.to_owned(),
                        ),
                        internal_chat_message_metadata_passthrough: None,
                    }),
                )
            }
            _ => (true, None),
        };
        if !keep {
            removed = removed.saturating_add(1);
            continue;
        }
        repaired.push(item);
        if let Some(stand_in) = stand_in {
            inserted = inserted.saturating_add(1);
            repaired.push(T::from(stand_in));
        }
    }
    (repaired, inserted, removed)
}

fn is_tool_output(item: &ResponseItem) -> bool {
    matches!(
        item,
        ResponseItem::FunctionCallOutput { .. } | ResponseItem::CustomToolCallOutput { .. }
    )
}

fn is_call_family(item: &ResponseItem) -> bool {
    matches!(
        item,
        ResponseItem::FunctionCall { .. }
            | ResponseItem::CustomToolCall { .. }
            | ResponseItem::LocalShellCall { .. }
            | ResponseItem::ToolSearchCall { .. }
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use codex_protocol::ResponseItemId;
    use codex_protocol::models::FunctionCallOutputPayload;
    use codex_protocol::models::ReasoningItemContent;

    fn reasoning(plain: bool, encrypted: bool) -> ResponseItem {
        ResponseItem::Reasoning {
            id: Some(ResponseItemId::from_server("reasoning".to_owned())),
            summary: vec![],
            content: plain.then(|| {
                vec![ReasoningItemContent::ReasoningText {
                    text: "private".to_owned(),
                }]
            }),
            encrypted_content: encrypted.then(|| "ciphertext".to_owned()),
            internal_chat_message_metadata_passthrough: None,
        }
    }

    fn message(role: &str, text: &str) -> ResponseItem {
        ResponseItem::Message {
            id: Some(ResponseItemId::from_server("message".to_owned())),
            role: role.to_owned(),
            content: vec![ContentItem::InputText {
                text: text.to_owned(),
            }],
            phase: None,
            internal_chat_message_metadata_passthrough: None,
        }
    }

    fn resize_notice() -> ResponseItem {
        message(
            "developer",
            "\n<image_resize_notice>\nImage 1 of 1 in the preceding tool output was resized from \
             1414x2000 to 1334x1888 pixels.\n</image_resize_notice>\n",
        )
    }

    fn function_call(call_id: &str) -> ResponseItem {
        ResponseItem::FunctionCall {
            id: None,
            name: "view_image".to_owned(),
            namespace: None,
            arguments: "{\"path\":\"fixture\"}".to_owned(),
            call_id: call_id.to_owned(),
            encrypted_function_args: None,
            internal_chat_message_metadata_passthrough: None,
        }
    }

    fn text_output(call_id: &str, text: &str) -> ResponseItem {
        ResponseItem::FunctionCallOutput {
            id: None,
            call_id: Some(call_id.to_owned()),
            name: Some("view_image".to_owned()),
            namespace: None,
            output: FunctionCallOutputPayload::from_text(text.to_owned()),
            internal_chat_message_metadata_passthrough: None,
        }
    }

    fn image_output(call_id: &str) -> ResponseItem {
        ResponseItem::FunctionCallOutput {
            id: None,
            call_id: Some(call_id.to_owned()),
            name: Some("view_image".to_owned()),
            namespace: None,
            output: FunctionCallOutputPayload::from_content_items(vec![
                FunctionCallOutputContentItem::InputImage {
                    image_url: "data:image/png;base64,AAAA".to_owned(),
                    detail: None,
                },
            ]),
            internal_chat_message_metadata_passthrough: None,
        }
    }

    fn output_text(item: &ResponseItem) -> Option<String> {
        let ResponseItem::FunctionCallOutput { output, .. } = item else {
            return None;
        };
        if let Some(text) = output.text_content() {
            return Some(text.to_owned());
        }
        let parts = output.content_items()?;
        let mut joined = String::new();
        for part in parts {
            if let FunctionCallOutputContentItem::InputText { text } = part {
                joined.push_str(text);
            }
        }
        Some(joined)
    }

    fn assert_transport_shape(items: &[ResponseItem]) {
        for (index, item) in items.iter().enumerate() {
            if is_tool_output(item) {
                if let Some(previous) = index.checked_sub(1).and_then(|i| items.get(i)) {
                    assert!(
                        !matches!(previous, ResponseItem::Message { .. }),
                        "a message item must never directly precede a tool output"
                    );
                }
            }
        }
        let mut calls = std::collections::HashSet::new();
        let mut outputs = std::collections::HashSet::new();
        for item in items {
            match item {
                ResponseItem::FunctionCall { call_id, .. } => {
                    assert!(
                        !calls.contains(call_id),
                        "call ids must stay unique inside a prompt copy"
                    );
                    calls.insert(call_id);
                }
                ResponseItem::FunctionCallOutput { call_id, .. } => {
                    outputs.insert(call_id.clone());
                }
                _ => {}
            }
        }
        for call_id in calls {
            assert!(
                outputs.contains(&Some(call_id.to_owned())),
                "every function call must keep a matching output"
            );
        }
    }

    #[test]
    fn openai_keeps_encrypted_only_reasoning() {
        let keep = message("user", "keep");
        assert_eq!(
            sanitize_prompt_history(
                "openai",
                vec![reasoning(true, false), keep.clone(), reasoning(false, true)]
            ),
            vec![keep, reasoning(false, true)]
        );
    }

    #[test]
    fn openai_rejects_hybrid_reasoning() {
        assert!(sanitize_prompt_history("openai", vec![reasoning(true, true)]).is_empty());
    }

    #[test]
    fn openai_provider_identity_is_case_insensitive() {
        assert_eq!(
            sanitize_prompt_history("OpenAI", vec![reasoning(false, true)]),
            vec![reasoning(false, true)]
        );
    }

    #[test]
    fn third_party_keeps_plaintext_and_rejects_encrypted() {
        assert_eq!(
            sanitize_prompt_history("kimi", vec![reasoning(false, true), reasoning(true, true)]),
            vec![reasoning(true, true)]
        );
    }

    #[test]
    fn annotated_items_preserve_metadata_and_order() {
        let keep = ResponseItemEnvelope::new(message("user", "keep"));
        assert_eq!(
            sanitize_prompt_history_annotated(
                "openai",
                vec![
                    ResponseItemEnvelope::new(reasoning(true, false)),
                    keep.clone(),
                    ResponseItemEnvelope::new(reasoning(false, true))
                ]
            ),
            vec![keep, ResponseItemEnvelope::new(reasoning(false, true))]
        );
    }

    #[test]
    fn non_reasoning_items_and_tool_pair_are_preserved_exactly() {
        let function_call = function_call("call-1");
        let function_output = text_output("call-1", "fixture result");
        let keep = vec![message("user", "keep"), function_call, function_output];
        let mut input = vec![reasoning(true, false)];
        input.extend(keep.clone());
        assert_eq!(sanitize_prompt_history("openai", input), keep);
    }

    #[test]
    fn openai_prompt_copy_keeps_notice_messages_untouched() {
        let input = vec![
            function_call("call-a"),
            function_call("call-b"),
            image_output("call-a"),
            resize_notice(),
            image_output("call-b"),
        ];
        assert_eq!(sanitize_prompt_history("openai", input.clone()), input);
    }

    #[test]
    fn deepseek_prompt_copy_folds_notice_into_preceding_output() {
        let normalized = sanitize_prompt_history(
            "deepseek",
            vec![
                function_call("call-a"),
                function_call("call-b"),
                image_output("call-a"),
                resize_notice(),
                image_output("call-b"),
            ],
        );
        assert_transport_shape(&normalized);
        assert_eq!(normalized.len(), 4);
        assert!(
            output_text(&normalized[2])
                .is_some_and(|text| text.contains(IMAGE_RESIZE_NOTICE_START)),
            "the notice must stay attached to the output it describes"
        );
    }

    #[test]
    fn notice_directly_before_its_output_is_relocated() {
        let normalized = sanitize_prompt_history(
            "deepseek",
            vec![
                function_call("call-a"),
                resize_notice(),
                image_output("call-a"),
            ],
        );
        assert_transport_shape(&normalized);
        assert_eq!(normalized.len(), 3);
        // The notice cannot be folded into a call, so it moves in front of the call
        // instead of staying between the call and its output.
        assert!(matches!(normalized[0], ResponseItem::Message { .. }));
        assert_eq!(normalized[1], function_call("call-a"));
        assert_eq!(normalized[2], image_output("call-a"));
    }

    #[test]
    fn user_message_between_outputs_is_moved_off_the_output() {
        let normalized = sanitize_prompt_history(
            "deepseek",
            vec![
                function_call("call-a"),
                function_call("call-b"),
                text_output("call-a", "a"),
                message("user", "steer"),
                text_output("call-b", "b"),
            ],
        );
        assert_transport_shape(&normalized);
        assert_eq!(normalized.len(), 5);
        // The steering message moves in front of the call whose output it preceded.
        assert_eq!(normalized[0], function_call("call-a"));
        assert_eq!(normalized[1], message("user", "steer"));
        assert_eq!(normalized[2], function_call("call-b"));
    }

    /// Regression for the real four-image payload: developer and user history
    /// plus the assistant turn text precede the call batch and must stay there.
    /// Only the resize notices fold into the outputs they describe.
    #[test]
    fn history_messages_before_the_call_batch_stay_in_place() {
        let normalized = sanitize_prompt_history(
            "deepseek",
            vec![
                message("developer", "<skills_instructions>"),
                message("user", "<environment_context>"),
                message("user", "review all four pages"),
                message("assistant", "I'll load all four images in parallel."),
                function_call("call-a"),
                function_call("call-b"),
                image_output("call-a"),
                resize_notice(),
                image_output("call-b"),
                resize_notice(),
            ],
        );
        assert_transport_shape(&normalized);
        assert_eq!(normalized.len(), 8);
        assert_eq!(normalized[0], message("developer", "<skills_instructions>"));
        assert_eq!(normalized[1], message("user", "<environment_context>"));
        assert_eq!(normalized[2], message("user", "review all four pages"));
        assert_eq!(
            normalized[3],
            message("assistant", "I'll load all four images in parallel.")
        );
        assert_eq!(normalized[4], function_call("call-a"));
        assert_eq!(normalized[5], function_call("call-b"));
        assert!(
            output_text(&normalized[6])
                .is_some_and(|text| text.contains(IMAGE_RESIZE_NOTICE_START))
        );
        assert!(
            output_text(&normalized[7])
                .is_some_and(|text| text.contains(IMAGE_RESIZE_NOTICE_START))
        );
    }

    #[test]
    fn dangling_call_receives_placeholder_output() {
        let normalized = sanitize_prompt_history(
            "deepseek",
            vec![function_call("call-a"), message("user", "next")],
        );
        assert_transport_shape(&normalized);
        assert_eq!(normalized.len(), 3);
        assert!(
            output_text(&normalized[1])
                .is_some_and(|text| text.contains("omitted before transport"))
        );
    }

    #[test]
    fn orphan_output_is_removed() {
        let normalized = sanitize_prompt_history(
            "deepseek",
            vec![
                function_call("call-a"),
                text_output("call-a", "a"),
                text_output("call-b", "b"),
            ],
        );
        assert_transport_shape(&normalized);
        assert_eq!(normalized.len(), 2);
    }

    #[test]
    fn annotated_copy_keeps_metadata_and_pairs_inserted_output() {
        let mut kept = ResponseItemEnvelope::new(function_call("call-a"));
        kept.metadata = Some(codex_history::CodexHarnessMetadata {
            client_authored: true,
            fallback_token_limit_override: None,
            ..Default::default()
        });
        let normalized = sanitize_prompt_history_annotated(
            "deepseek",
            vec![
                kept.clone(),
                ResponseItemEnvelope::new(message("user", "next")),
            ],
        );
        assert_eq!(normalized[0], kept);
        assert_eq!(normalized[1].metadata, None);
        assert!(matches!(
            normalized[1].item,
            ResponseItem::FunctionCallOutput { .. }
        ));
    }

    /// Replays a synthetic failing batch (four tool calls, four outputs, and one
    /// notice after each output) and proves the outbound copy is transportable.
    /// Setting `CODEX_SHAPE_FIXTURE_OUT`
    /// dumps the normalized items so the same payload can be replayed against the
    /// provider endpoint; `CODEX_SHAPE_FIXTURE_RAW_OUT` dumps the un-normalized
    /// items for the negative control.
    #[test]
    fn synthetic_notice_batch_is_transportable() {
        let fixture: serde_json::Value = serde_json::from_str(include_str!(
            "prompt_history_compat_fixtures/deepseek_notice_batch.json"
        ))
        .expect("fixture json");
        let items: Vec<ResponseItem> = fixture["items"]
            .as_array()
            .expect("items array")
            .iter()
            .map(|value| serde_json::from_value(value.clone()).expect("response item"))
            .collect();
        assert_eq!(items.len(), 12);

        let normalized = sanitize_prompt_history("deepseek", items.clone());
        assert_transport_shape(&normalized);
        assert!(
            normalized
                .iter()
                .filter(|item| matches!(item, ResponseItem::Message { .. }))
                .count()
                == 0,
            "every recorded resize notice must be folded into the item it describes"
        );

        if let Ok(path) = std::env::var("CODEX_SHAPE_FIXTURE_OUT") {
            let raw: Vec<serde_json::Value> = normalized
                .iter()
                .map(|item| serde_json::to_value(item).expect("serialize item"))
                .collect();
            std::fs::write(path, serde_json::to_vec_pretty(&raw).expect("encode")).expect("write");
        }
        if let Ok(path) = std::env::var("CODEX_SHAPE_FIXTURE_RAW_OUT") {
            let raw: Vec<serde_json::Value> = items
                .iter()
                .map(|item| serde_json::to_value(item).expect("serialize item"))
                .collect();
            std::fs::write(path, serde_json::to_vec_pretty(&raw).expect("encode")).expect("write");
        }
    }
}
