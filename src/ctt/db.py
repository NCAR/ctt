from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy import func

timestamp = Annotated[
    datetime.datetime,
    mapped_column(nullable=False, server_default=func.CURRENT_TIMESTAMP()),
]

class Base(DeclarativeBase):
    pass

class Issue(Base):
    #TODO use constants for mapped_column string length
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(30)) 
    description: Mapped[str] = mapped_column(String(300))
    host: Mapped[str] = mapped_column(String(30))
    ticket: Mapped[Optional[str]]
    status: Mapped[Status]
    host_state: Mapped[State]
    sibling_state: Mapped[Optional[State]]
    severity: Mapped[int]
    assigned_to: Mapped[Optional[str]] = mapped_column(String(30))
    created_by: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[timestamp]
    updated_at: Mapped[timestamp] = mapped_column(onupdate=datetime.datetime.now)
    type: Mapped[TicketType]

    comments: Mapped[List["Comment"]] = relationship(back_populates("issues", cascade="all, delete-orphan"))

    def __repr__(self) -> str:
        return f"Issue(id={self.id}, title={self.title}, description={self.description}, host={self.host}, ticket={self.ticket}, status={self.status}, host_state={self.host_state}, sibling_state={self.sibling_state}, severity={self.severity}, assigned_to={self.assigned_to}, created_by={self.created_by}, created_at={self.created_at}, updated_at={self.updated_at}, type={self.type})"

class Status(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"

class State(enum.Enum):
    ONLINE = "online"
    OFF = "off"
    DRAINING = "draining"
    DRAINED = "drained"

class TicketType(enum.Enum):
    SOFTWARE = "software"
    HARDWARE = "hardware"

class Comment(Base):
    #TODO use constants for mapped_column string length
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"))
    created_at: Mapped[timestamp]
    created_by: Mapped[str] = mapped_column(String(30))
    comment: Mapped[str] = mapped_column(String(300))

    issue: Mapped["Issue"] = relationship(back_populates("comments"))

    def __repr__(self) -> str:
        return f"Comment(id={self.id}, issue_id={self.issue_id}, created_at={self.created_at}, created_by={self.created_by}, comment={self.comment})"


class DB:
    def __init__(self, conf):
        db = conf.get("db", "db")
        db_type = conf.get("db", "type")
        db_api = conf.get("db", "api")
        self.engine = sqlalchemy.create_engine(f"{db_type}+{db_api}://{db}")
        self.session = sqlalchemy.Session(self.engine)

    def __del__(self):
        if self.session is not None:
            self.session.close()
            self.session = None

    def node_issues(self, node) -> (str):
        result = self.session.scalars(sqlalchemy.select(Issue).where(Issue.host = node))
        return result.all()

    def issue(self, cttissue):
        result = self.session.scalar(sqlalchemy.select(Issue).where(Issue.id == cttissue))
        return result.first()

    def new_issue(self, kwargs):
        newIssue = Issue(kwargs)
        self.session.add(newIssue)
        self.session.commit()
        return newIssue

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
