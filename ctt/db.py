import sqlite3 as sql


class Issue:
    def __init__(self, con, **kwargs):
        self._con = con

        self.cttissue = kwargs.get("cttissue")
        self.date = kwargs.get("date")
        self.severity = kwargs.get("severity")
        self.ticket = kwargs.get("ticket")
        self.status = kwargs.get("status")
        self.hostname = kwargs.get("hostname")
        self.title = kwargs.get("title")
        self.description = kwargs.get("description")
        self.assignedto = kwargs.get("assignedto")
        self.originator = kwargs.get("originator")
        self.updatedby = kwargs.get("updatedby")
        self.type = kwargs.get("type")
        self.state = kwargs.get("state")
        self.updatedtime = kwargs.get("updatedtime")
        self.viewtracker = kwargs.get("viewtracker")
        self.xticket = kwargs.get("xticket")

    def update(self, db):
        """Update all changed fields for the issue in the db"""
        if self.cttissue:
            self._con.execute(
                "UPDATE issues SET (date,severity,ticket,status,hostname,title,description,assignedto,originator,updatedby,type,state,updatedtime,viewtracker,xticket) = (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) WHERE rowid = ?",
                (
                    self.date,
                    self.severity,
                    self.ticket,
                    self.status,
                    self.hostname,
                    self.title,
                    self.description,
                    self.assignedto,
                    self.originator,
                    self.updatedby,
                    self.type,
                    self.state,
                    datetime.time.now(),
                    self.viewtracker,
                    self.xticket,
                    self.cttissue,
                ),
            )

        else:
            cur = self._con.execute(
                "INSERT issues SET (date,severity,ticket,status,hostname,title,description,assignedto,originator,updatedby,type,state,updatedtime,viewtracker,xticket) = (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    self.date,
                    self.severity,
                    self.ticket,
                    self.status,
                    self.hostname,
                    self.title,
                    self.description,
                    self.assignedto,
                    self.originator,
                    self.updatedby,
                    self.type,
                    self.state,
                    datetime.time.now(),
                    self.viewtracker,
                    self.xticket,
                ),
            )
            self.cttissue = cur.lastrowid


class DB:
    # TODO make sure db handles races correctly
    def __init__(self, config):
        self._file = config.get("db", "file")
        self._con = sql.connect(self._file)
        self._setup_db()

    def __del__(self):
        if self._con is not None:
            # commit any open transactions then close connection
            self._con.commit()
            self._con.close()

    def node_issue(self, node):
        con = sql.connect(self.file)
        with con:
            cur = con.cursor()
            cur.execute(
                """SELECT ? FROM issues WHERE hostname = ? and stats = open""", (node)
            )
            issue = cur.fetchone()
            if issue is not None:
                return issue_from_row(issue)
            else:
                return None

    def issue(self, cttissue):
        con = sql.connect(self.file)
        with con:
            cur = con.cursor()
            cur.execute("""SELECT ? FROM issues WHERE rowid = ?""", (field, cttissue))
            issue = cur.fetchone()
            if issue is not None:
                return issue_from_row(issue)
            else:
                return None

    def new_issue(self, kwargs):
        return Issue(self._con, kwargs)

    def setup_db(self):
        # sqlite tables automatically have a rowid primary key column
        self._con.execute(
            """CREATE TABLE IF NOT EXISTS issues(
            date TEXT NOT NULL,
            severity INT NOT NULL,
            ticket TEXT,
            status TEXT NOT NULL,
            hostname TEXT NOT NULL,
            issuetitle TEXT NOT NULL,
            issuedescription TEXT NOT NULL,
            assignedto TEXT,
            issueoriginator TEXT NOT NULL,
            updatedby TEXT NOT NULL,
            issuetype TEXT NOT NULL,
            state TEXT,
            updatedtime TEXT,
            viewtracker TEXT,
            xticket TEXT)"""
        )

        self._con.execute(
            """CREATE TABLE IF NOT EXISTS comments(
            cttissue TEXT NOT NULL,
            date TEXT NOT NULL,
            updatedby TEXT NOT NULL,
            comment TEXT NOT NULL)"""
        )

        self._con.execute(
            """CREATE TABLE IF NOT EXISTS history(
            cttissue TEXT NOT NULL,
            date TEXT NOT NULL,
            updatedby TEXT NOT NULL,
            info TEXT)"""
        )

        self._con.execute(
            """CREATE TABLE IF NOT EXISTS holdback(
            hostname TEXT NOT NULL,
            state TEXT NOT NULL)"""
        )

        self._con.execute(
            """CREATE TABLE IF NOT EXISTS siblings(
                cttissue TEXT NOT NULL,
                date TEXT NOT NULL,
                status TEXT NOT NULL,
                parent TEXT NOT NULL,
                sibling TEXT NOT NULL,
		state TEXT)"""
        )

    def issue_siblings(self, cttissue):
        cur = self._con.execute(
            """SELECT sibling, FROM siblings WHERE cttissue = ? AND status = open""",
            (cttissue),
        )
        return [r[0] for r in cur]

    def node_sib_of(self, node):
        cur = self._con.execute(
            """SELECT cttissue FROM siblings WHERE sibling = ? AND status = open""",
            (node),
        )
        issues = []
        for r in cur:
            issues.append(r[0])
        return issues

    def release_sib(self, cttissue, node):
        self._con.execute(
            """UPDATE siblings SET status = closed WHERE cttissue = ? AND sibling = ?""",
            (cttissue, node),
        )

    def related_issues(self, node):
        issue = self.node_issue(node)
        sibissues = self.node_sib_of(node)
        if issue is None:
            return sibissues
        else:
            if len(sibissues) == 0:
                return [issue]
            else:
                sibissues.append(issue)
                return sibissues

    def issue_close(self, cttissue):
        con = sql.connect(self.file)
        with con:
            con.execute(
                """UPDATE issues SET status = closed WHERE rowid = ?""", (cttissue)
            )

    def cttissue(self, node):
        con = sql.connect(self.file)
        with con:
            cur = con.execute(
                """SELECT rowid FROM issues WHERE hostname = ? and status = 'open' LIMIT 1""",
                (node),
            )
            issue = cur.fetchone()
            if issue:
                return issue[0]
            else:
                return None

    def delete_issue(self, cttissue):
        self.update_issue_status(cttissue, "deleted")

    def update_issue_status(self, cttissue, status):
        con = sql.connect(self.file)
        with con:
            cur.execute(
                """UPDATE issues SET status = ? WHERE rowid =?""", (status, cttissue)
            )

    def update_ticket(self, cttissue, ticket):
        con = SQL.connect("ctt.sqlite")
        with con:
            con.execute(
                """UPDATE issues SET ticket = ? WHERE rowid = ?""",
                (ticketvalue, cttissue),
            )

    def get_hostname(self, cttissue):
        return self.issue_field(cttissue, "hostname")

    def get_status(self, cttissue):
        return self.issue_field(cttissue, "status")

    def get_ticket(self, cttissue):
        return self.issue_field(cttissue, "ticket")

    def issue_field(self, cttissue, field):
        con = sql.connect(self.file)
        with con:
            cur = con.cursor()
            cur.execute("""SELECT ? FROM issues WHERE rowid = ?""", (field, cttissue))
            field = cur.fetchone()
            if field is not None:
                return field[0]
            else:
                return None

    def open_count(self):
        con = sql.connect(self.file)
        with con:
            cur = con.cursor()
            cur.execute("""SELECT count(*) FROM issues WHERE status = open""")
            issues = cur.fetchone()
            if issues is None:
                return 0
            else:
                return int(issues[0])

    def maxissueopen(self):
        cur = self._con.execute(
            """SELECT * FROM issues WHERE status = open and issuetitle = ? LIMIT 1""",
            ("MAX OPEN REACHED"),
        )
        return cur.fetchone() is not None

    def get_history(self, cttissue):  # used only when issuing --show with -d option
        if issue_exists_check(cttissue):
            cols = "{0:<24}{1:<14}{2:<50}"
            fmt = cols.format
            print("\n----------------------------------------")
            print(fmt("DATE", "UPDATE.BY", "INFO"))
            con = SQL.connect(self.file)
            with con:
                cur = con.cursor()
                cur.execute("""SELECT * FROM history WHERE cttissue = ?""", (cttissue,))
                for row in cur:
                    date = row[2][0:16]
                    updatedby = row[3]
                    info = row[4]

                    # TODO return history instead of printing
                    print(
                        fmt(
                            "%s" % date,
                            "%s" % updatedby,
                            "%s" % textwrap.fill(info, width=80),
                        )
                    )

    def log_history(self, cttissue, date, updatedby, info):
        if (
            issue_deleted_check(cttissue) is False
            or issue_exists_check(cttissue) is True
        ):
            con = SQL.connect(self.file)
            with con:
                cur = con.cursor()
                cur.execute(
                    """INSERT INTO history(
                         cttissue,date,updatedby,info)
                         VALUES(?, ?, ?, ?)""",
                    (cttissue, date, updatedby, info),
                )

    def update_holdback(self, node, state):
        con = SQL.connect(self.file)
        with con:
            if "remove" in state:
                con.execute(
                    """UPDATE holdback SET state = ? WHERE hostname = ? and state = ?""",
                    (
                        "False",
                        node,
                        " True",
                    ),
                )
            if "add" in state:
                con.execute(
                    """INSERT INTO holdback(
                         hostname,state)
                         VALUES(?, ?)""",
                    (node, "True"),
                )

    def update_xticket(self, cttissue, xticketvalue):
        con = SQL.connect(self.file)
        with con:
            cur = con.execute("""SELECT * FROM issues WHERE rowid = ?""", (cttissue,))
            for row in cur:
                xticketlist = row[17]  ## CHECK THIS
                xticketlist = xticketlist.split(",")
                if "---" in xticketlist:
                    xticketlist.remove("---")
                if xticketvalue in xticketlist:
                    xticketlist.remove(xticketvalue)
                else:
                    xticketlist.append(xticketvalue)
                xticketlist = ",".join(xticketlist)
                if not xticketlist:
                    xticketlist = "---"
                cur.execute(
                    """UPDATE issues SET xticket = ? WHERE rowid = ?""",
                    (
                        xticketlist,
                        cttissue,
                    ),
                )

    def update_view_tracker(self, cttissue, userlist):
        con = SQL.connect(self.file)
        with con:
            cur.execute(
                """UPDATE issues SET viewtracker = ? WHERE rowid = ?""",
                (userlist, cttissue),
            )

    def issue_from_row(self, row):
        args = {}
        args["cttissue"] = row[1]
        args["date"] = row[2][0:16]
        args["severity"] = row[3]
        args["ticket"] = row[4]
        args["status"] = row[5]
        args["hostname"] = row[6]
        args["title"] = row[7]
        args["description"] = row[8]
        args["assignedto"] = row[9]
        args["originator"] = row[10]
        args["updatedby"] = row[11]
        args["issuetype"] = row[12]
        args["state"] = row[13]
        args["updatedtime"] = row[14][0:16]
        args["viewtracker"] = row[15]
        args["xticket"] = row[16]
        return Issue(args)

    def get_comments(cttissue):  # used for --show option (displays the comments)
        if self.issue(cttissue):
            comments = []
            cur = self.con.execute(
                """SELECT * FROM comments WHERE cttissue = ?""", (cttissue,)
            )
            for row in cur:
                date = row[2][0:16]
                updatedby = row[3]
                comment = row[4]
                comments.append((updatedby, date, comment))
            return comments

    def comment_issue(cttissue, date, updatedby, newcomment):
        if self.issue(cttissue):
            con.execute(
                """INSERT INTO comments(
                    cttissue,date,updatedby, comment)
                    VALUES(?, ?, ?, ?)""",
                (cttissue, date, updatedby, newcomment),
            )
        else:
            print("Can't add comment to %s. Issue not found or deleted" % (cttissue))

    def get_issues(statustype):
        if "all" == statustype:
            cur = self._con.execute("""SELECT * FROM issues ORDER BY rowid ASC""")
        else:
            cur = self._con.execute(
                """SELECT * FROM issues WHERE status = ? ORDER BY rowid ASC""",
                (statustype),
            )
        issues = []
        for row in cur:
            issues.append(self.issue_from_row(row))
        return issues
