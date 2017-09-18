from app import db
from uuid import uuid1 as uuid

class operationLog(db.Model):
    __tablename__= "ansible_operation_log"
    id = db.Column(db.String(255),primary_key=True)
    cmd = db.Column(db.String(1000))
    status = db.Column(db.String(64))
    result = db.Column(db.String(5000))

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