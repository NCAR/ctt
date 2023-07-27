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
    description: orm.Mapped[Optional[str]] = orm.mapped_column(sqlalchemy.String(300))
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
    type: orm.Mapped[Optional[IssueType]]
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
        if "down_siblings" in kwargs:
            statment = statment.where(Issue.down_siblings == kwargs["down_siblings"])
        if "title" in kwargs:
            statment = statment.where(Issue.title == kwargs["title"])
        return self.session.scalars(statment).all()
