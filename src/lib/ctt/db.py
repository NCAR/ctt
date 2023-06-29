import datetime
import enum
import typing
from typing import List, Optional

import sqlalchemy
import sqlalchemy.orm as orm

timestamp = typing.Annotated[
    datetime.datetime,
    orm.mapped_column(
        nullable=False, server_default=sqlalchemy.func.CURRENT_TIMESTAMP()
    ),
]


class Base(orm.DeclarativeBase):
    pass


class IssueStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"

class IssueType(enum.Enum):
    SOFTWARE = "software"
    HARDWARE = "hardware"


class Issue(Base):
    # TODO use constants for orm.mapped_column string length
    __tablename__ = "issues"

    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    title: orm.Mapped[str] = orm.mapped_column(sqlalchemy.String(30))
    description: orm.Mapped[str] = orm.mapped_column(sqlalchemy.String(300))
    ticket: orm.Mapped[Optional[str]]
    status: orm.Mapped[IssueStatus]
    target: orm.Mapped[str]
    down_siblings: orm.Mapped[bool]
    severity: orm.Mapped[int]
    assigned_to: orm.Mapped[Optional[str]] = orm.mapped_column(sqlalchemy.String(30))
    created_by: orm.Mapped[str] = orm.mapped_column(sqlalchemy.String(30))
    created_at: orm.Mapped[timestamp]
    updated_at: orm.Mapped[timestamp] = orm.mapped_column(
        onupdate=datetime.datetime.now
    )
    type: orm.Mapped[IssueType]
    enforce_down: orm.Mapped[bool] = orm.mapped_column(default=False)

    comments: orm.Mapped[List["Comment"]] = orm.relationship(
        back_populates="issue", cascade="all, delete-orphan", order_by='Comment.created_at'
    )

    def __repr__(self) -> str:
        return f"Issue(id={self.id}, title={self.title}, description={self.description}, ticket={self.ticket}, status={self.status}, target={self.target}, down_siblings={self.down_siblings}, severity={self.severity}, assigned_to={self.assigned_to}, created_by={self.created_by}, created_at={self.created_at}, updated_at={self.updated_at}, type:{self.type}, enforce_down={self.enforce_down})"


class Comment(Base):
    # TODO use constants for orm.mapped_column string length
    __tablename__ = "comments"

    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    issue_id: orm.Mapped[int] = orm.mapped_column(sqlalchemy.ForeignKey("issues.id"))
    created_at: orm.Mapped[timestamp]
    created_by: orm.Mapped[str] = orm.mapped_column(sqlalchemy.String(30))
    comment: orm.Mapped[str] = orm.mapped_column(sqlalchemy.String(300))

    issue: orm.Mapped["Issue"] = orm.relationship(back_populates="comments")

    def __repr__(self) -> str:
        return f"Comment(id={self.id}, issue_id={self.issue_id}, created_at={self.created_at}, created_by={self.created_by}, comment={self.comment})"


class DB:
    def __init__(self, conf):
        db = conf['db']
        db_type = conf["type"]
        url = f'{db_type}:///{db}'
        # add echo=True to create_enginge to see raw sql in stdout
        self.engine = sqlalchemy.create_engine(url)
        self.session = orm.Session(self.engine)
        Base.metadata.create_all(self.engine)

    def __del__(self):
        if self.session is not None:
            self.session.close()
            self.session = None

    def update(self):
        self.session.commit()

    def issue(self, cttissue) -> Issue:
        return self.session.scalar(
            sqlalchemy.select(Issue).where(Issue.id == cttissue)
        )

    def new_issue(self, issue) -> int:
        self.session.add(issue)
        self.session.commit()
        return issue.id

    def get_issues(self, **kwargs):
        statment = sqlalchemy.select(Issue)
        if "status" in kwargs:
            statment = statment.where(Issue.status == kwargs["status"])
        if "target" in kwargs:
            #TODO also get issues where a nodes IRU/chassis is the target
            statment = statment.where(Issue.target == kwargs["target"])
        return self.session.scalars(statment).all()



'''
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
                """SELECT rowid FROM issues WHERE nodename = ? and status = 'open' LIMIT 1""",
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

    def get_nodename(self, cttissue):
        return self.issue_field(cttissue, "nodename")

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
                    """UPDATE holdback SET state = ? WHERE nodename = ? and state = ?""",
                    (
                        "False",
                        node,
                        " True",
                    ),
                )
            if "add" in state:
                con.execute(
                    """INSERT INTO holdback(
                         nodename,state)
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

    def get_comments(self, cttissue):  # used for --show option (displays the comments)
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

    def comment_issue(self, cttissue, date, updatedby, newcomment):
        if self.issue(cttissue):
            con.execute(
                """INSERT INTO comments(
                    cttissue,date,updatedby, comment)
                    VALUES(?, ?, ?, ?)""",
                (cttissue, date, updatedby, newcomment),
            )
        else:
            print("Can't add comment to %s. Issue not found or deleted" % (cttissue))

    def get_issues(self, statustype):
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
'''
