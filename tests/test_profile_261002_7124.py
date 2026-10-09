import hashlib,unittest
import build_backend as b

class CurrentSourceProfile(unittest.TestCase):
    def test_exact_new_profile_and_complete_migration_contract(self):
        folder,data=b.load_profile('desktop-26.1002.7124.0-sqlite-v2')
        self.assertEqual(data['upstream_commit'],'74e804deeb1241d5fe699b31fb319f7d46454c42')
        self.assertEqual(data['version'],'0.162.0-alpha.2')
        self.assertEqual(data['rust_toolchain'],'1.95.0')
        self.assertEqual(data['build_jobs'],2)
        self.assertTrue(data['focused_release_tests'])
        rows=b.migration_rows(folder,data)
        self.assertEqual(len(rows),74)
        self.assertEqual(len({r['source_path'] for r in rows}),74)
        self.assertTrue(all(len(r['sqlx_sha384'])==96 for r in rows))
        self.assertEqual(len(data['source_files']),7)

    def test_profile_hashes_survive_source_download_line_endings(self):
        folder,data=b.load_profile('desktop-26.1002.7124.0-sqlite-v2')
        for name,expected in data['files'].items():
            raw=(folder/name).read_bytes()
            self.assertNotIn(b'\r\n',raw,name)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),expected)

if __name__=='__main__':unittest.main()
