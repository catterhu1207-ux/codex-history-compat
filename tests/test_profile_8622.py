import hashlib,json,unittest
from test_profiles import recipe

class Profile8622(unittest.TestCase):
    def test_source_toolchain_and_migration_inventory_are_consistent(self):
        folder,p=recipe.load_profile('desktop-26.1016.8622.0-sqlite-v2')
        old_folder,old=recipe.load_profile('desktop-26.1016.8120.0-sqlite-v2')
        self.assertEqual(p['upstream_commit'],'51f97c6bca5500edbb986f6d9fe64fa2e63cbdd4')
        self.assertEqual(p['rust_toolchain'],'1.99.1')
        self.assertEqual(p['version'],'0.163.0-alpha.11.2.1')
        self.assertEqual(p['source_files'],old['source_files'])
        inventory=json.loads((folder/p['sqlite_migrations']).read_bytes())
        self.assertEqual(inventory['upstream_commit'],p['upstream_commit'])
        self.assertEqual(inventory['official_backend_sha256'],p['official_backend_sha256'])
        self.assertEqual(recipe.migration_rows(folder,p),recipe.migration_rows(old_folder,old))
        self.assertEqual(len(inventory['migrations']),77)
        self.assertNotEqual(p['official_backend_sha256'],old['official_backend_sha256'])
        with self.assertRaisesRegex(ValueError,'migration_upstream_commit_mismatch'):
            recipe.migration_rows(folder,{**p,'upstream_commit':old['upstream_commit']})

    def test_release_equivalence_is_bound_to_exact_source_and_asset(self):
        _,p=recipe.load_profile('desktop-26.1016.8622.0-sqlite-v2')
        e=p['official_backend_equivalence']
        self.assertEqual(e['upstream_release_commit'],p['upstream_commit'])
        self.assertEqual(e['upstream_release_tag'],'rust-v'+p['upstream_version'])
        self.assertTrue(e['all_named_sections_identical'])
        for k in ('upstream_release_asset_sha256','upstream_backend_sha256','unsigned_body_sha256_with_zero_checksum'):
            self.assertEqual(len(bytes.fromhex(e[k])),32)

    def test_all_profiles_have_consistent_optional_migration_source(self):
        for file in (recipe.ROOT/'profiles').glob('*/profile.json'):
            with self.subTest(profile=file.parent.name):
                folder,p=recipe.load_profile(file.parent.name)
                if not p.get('sqlite_migrations'):continue
                m=json.loads((folder/p['sqlite_migrations']).read_bytes())
                if 'upstream_commit' in m:self.assertEqual(m['upstream_commit'],p['upstream_commit'])
                self.assertEqual(m['official_backend_sha256'],p['official_backend_sha256'])

if __name__=='__main__':unittest.main()
