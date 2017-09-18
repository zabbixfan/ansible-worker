from app import db
from uuid import uuid1 as uuid

class ipPool(db.Model):
    __tablename__= "workflow_ipPool"
    id = db.Column(db.String(255),primary_key=True)
    ip = db.Column(db.String(255))
    name = db.Column(db.String(255))
    status = db.Column(db.String(32),default='false')
    hostServer = db.Column(db.String(255))

    def save(self,wait_commit=False):
        if not self.id:
            self.id=uuid().get_hex()
        db.session.add(self)
        if wait_commit:
            db.session.flush()
        else:
            db.session.commit()
    @staticmethod
    def commit():
        db.session.commit()