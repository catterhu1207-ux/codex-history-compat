import hashlib,json,tempfile,unittest
from pathlib import Path
from test_profiles import recipe

class SqliteMigrations(unittest.TestCase):
    def test_cached_binary_missing_auxiliary_digest_recompiles_state_without_editing_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);crate=root/'codex-rs/state/src/lib.rs'
            crate.parent.mkdir(parents=True);crate.write_bytes(b'// migration crate\n')
            import os
            os.utime(crate,(1,1));before=crate.read_bytes()
            binary=root/'codex.exe';binary.write_bytes(b'old')
            rows=[{'sqlx_sha384':hashlib.sha384(b'auxiliary').hexdigest()}]
            self.assertTrue(recipe.invalidate_stale_migration_cache(root,binary,rows))
            self.assertGreater(crate.stat().st_mtime,1)
            self.assertEqual(crate.read_bytes(),before)
            binary.write_bytes(bytes.fromhex(rows[0]['sqlx_sha384']))
            stamp=crate.stat().st_mtime_ns
            self.assertFalse(recipe.invalidate_stale_migration_cache(root,binary,rows))
            self.assertEqual(crate.stat().st_mtime_ns,stamp)
    def fixture(self, root):
        rows=[]
        for folder in ('migrations','logs_migrations','goals_migrations','memory_migrations','queue_migrations','thread_history_migrations'):
            path='codex-rs/state/'+folder+'/0001_init.sql'
            raw=('CREATE TABLE '+folder+'(id TEXT);\n').encode()
            file=root/path;file.parent.mkdir(parents=True);file.write_bytes(raw)
            expected=raw.replace(b'\n',b'\r\n')
            rows.append(dict(source_path=path,sha256=hashlib.sha256(expected).hexdigest(),sqlx_sha384=hashlib.sha384(expected).hexdigest()))
        return rows
    def test_every_database_uses_official_windows_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);rows=self.fixture(root)
            recipe.qualify_migration_bytes(root,rows,all_databases=True,official_bytes=b''.join(bytes.fromhex(r['sqlx_sha384']) for r in rows))
            for row in rows:
                self.assertEqual(hashlib.sha384((root/row['source_path']).read_bytes()).hexdigest(),row['sqlx_sha384'])
    def test_state_only_inventory_rejects_existing_auxiliary_migrations(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);rows=self.fixture(root)
            before={r['source_path']:(root/r['source_path']).read_bytes() for r in rows}
            with self.assertRaisesRegex(ValueError,'inventory_mismatch'):
                recipe.qualify_migration_bytes(root,rows[:1],all_databases=True)
            self.assertTrue(all((root/p).read_bytes()==data for p,data in before.items()))
    def test_bad_auxiliary_digest_does_not_modify_any_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);rows=self.fixture(root);rows[-1]['sqlx_sha384']='0'*96
            before=(root/rows[0]['source_path']).read_bytes()
            with self.assertRaisesRegex(ValueError,'identity_mismatch'):
                recipe.qualify_migration_bytes(root,rows,all_databases=True)
            self.assertEqual((root/rows[0]['source_path']).read_bytes(),before)
    def test_official_binary_must_contain_every_digest(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);rows=self.fixture(root)
            with self.assertRaisesRegex(ValueError,'official_migration_missing'):
                recipe.qualify_migration_bytes(root,rows,all_databases=True,official_bytes=b'wrong')
    def test_duplicate_or_escaped_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);rows=self.fixture(root)
            for wrong in (rows+[rows[0]],[dict(rows[0],source_path='../outside.sql')]):
                with self.assertRaisesRegex(ValueError,'path_escape_or_duplicate'):
                    recipe.qualify_migration_bytes(root,wrong,all_databases=True)
    def test_new_profile_covers_all_72_without_changing_legacy_identity(self):
        folder,new=recipe.load_profile('desktop-26.924.2738.0-sqlite-v2')
        old_folder,old=recipe.load_profile('desktop-26.924.2738.0')
        rows=recipe.migration_rows(folder,new)
        self.assertEqual(len(rows),72)
        self.assertEqual(len({r['database'] for r in rows}),6)
        self.assertEqual(len(recipe.migration_rows(old_folder,old)),57)
        self.assertEqual(new['source_files'],old['source_files'])
        self.assertEqual(new['upstream_commit'],old['upstream_commit'])
