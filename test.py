#!/usr/bin/env python3
import configparser
import unittest
import unittest.mock as mock

import ctt
import cttlib


def make_config():
    conf = configparser.ConfigParser()
    conf["user"] = {"user": "myuser", "group": "mygroup"}
    conf["users"] = {"teams": "myteam1 myteam2"}
    conf["pbs"] = {"enabled": "True"}
    conf["slack"] = {"enabled": "False"}
    conf["cluster"] = {"name": "mycluster"}
    conf["ev"] = {"enabled": "False"}
    return conf


@mock.patch("datetime.datetime")
class TestCttlib(unittest.TestCase):
    def test_release(self, dt):
        """Test the happy case, release siblings from an issue"""
        with mock.patch("db.DB") as mockdb:
            dt.now().isoformat().return_value = "now"
            db = mockdb.return_value
            ev = mock.Mock()
            slack = mock.Mock()
            issue = mock.Mock()
            issue.cttissue = "myissue"
            ctt = cttlib.CTT(make_config())
            ctt.db = db
            self.ev = ev
            self.slack = slack
            db.issue.return_value = issue
            db.in_other_open_issue.return_value = False
            issue.hostname = "node1"
            ctt.release("myissue", "now", "node1")

            db_expected = [
                mock.call.issue("myissue"),
                mock.call.release_sib("myissue", "node1"),
                mock.call.log_history(
                    "myissue", "now", "myuser", "Released node node1 cttissue: myissue"
                ),
                mock.call.in_other_open_issue("myissue", "node1"),
                mock.call.log_history("myissue", "now", "myuser", "ctt resumed node1"),
            ]
            self.assertListEqual(db.mock_calls, db_expected)

    def test_release_primary(self, dt):
        """Test the case where one tries to release a node from its own ticket"""
        pass

    def test_release_not_on_ticket(self, dt):
        """Test the case where one tries to release a node from a ticket its not on"""
        pass

    def test_release_no_pbs(self, dt):
        """Test case where pbs is turned off"""
        pass


@mock.patch("datetime.datetime")
class TestCtt(unittest.TestCase):
    def test_release_single_node(self, dt):
        with mock.patch("cttlib.CTT") as mockcttlib:
            # Setup
            now = dt.Mock()
            now.isoformat.return_value = "now_iso"
            dt.now.return_value = now

            args = mock.Mock()
            args.node = ["mynode"]
            args.issue = "myissue"

            conf = mock.Mock()

            # Calling function under test
            ctt.release(args, conf)

            # Expected result
            expected = [mock.call.release("myissue", "now_iso", "mynode")]

            # Checking actual == expected
            instance = mockcttlib.return_value
            self.assertListEqual(instance.mock_calls, expected)

    def test_release_multi_node(self, dt):
        with mock.patch("cttlib.CTT") as mockcttlib:
            # Setup
            now = dt.Mock()
            now.isoformat.return_value = "now_iso"
            dt.now.return_value = now

            args = mock.Mock()
            args.node = ["mynode1", "mynode2", "mynode3"]
            args.issue = "myissue"

            conf = mock.Mock()

            # Calling function under test
            ctt.release(args, conf)

            # Expected result
            expected = [
                mock.call.release("myissue", "now_iso", "mynode1"),
                mock.call.release("myissue", "now_iso", "mynode2"),
                mock.call.release("myissue", "now_iso", "mynode3"),
            ]

            # Checking actual == expected
            instance = mockcttlib.return_value
            self.assertListEqual(instance.mock_calls, expected)


if __name__ == "__main__":
    unittest.main()
