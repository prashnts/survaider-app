#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#.--. .-. ... .... -. - ... .-.-.- .. -.

from datetime import datetime, timedelta
from mongoengine.queryset import queryset_manager

from flask.ext.security import current_user

from survaider.minions.helpers import HashId
from survaider.user.model import User
from survaider.survey.model import Survey, Response
from survaider import db, app

class Notification(db.Document):
    destined = db.ListField(db.ReferenceField(User))
    acquired = db.DateTimeField(default = datetime.now)
    released = db.DateTimeField(default = datetime.max)
    payload  = db.DictField()

    #: Enables Inheritance.
    meta = {'allow_inheritance': True}

    def __unicode__(self):
        return HashId.encode(self.id)

    @property
    def flagged(self):
        return datetime.now() > self.released

    @flagged.setter
    def flagged(self, value):
        if value is True:
            self.released = datetime.max
        else:
            #: Sets time two seconds behind, to eliminate ANY possibility of
            #  race conditions and prevents other bugs, in general.
            self.released = datetime.now() - timedelta(seconds = 2)

    @queryset_manager
    def past(doc_cls, queryset):
        return queryset.order_by('-acquired')

    @staticmethod
    def unflagged_count():
        return Notification.past(released__gt = datetime.now()).count()

class SurveyResponseNotification(Notification):
    survey   = db.ReferenceField(Survey, required = True)
    response = db.ReferenceField(Response, required = True)
    transmit = db.BooleanField(default = False)

    @property
    def resolved_payload(self):
        fields = self.survey.resolved_root.struct.get('fields', [])
        payload = []
        flat_payload = [_ for _ in self.payload]
        for field in fields:
            "Look for matching questions, resolve options"
            "Todo: Resolve Answers "
            if field.get('cid') in flat_payload:
                payload.append({
                    'cid':      field.get('cid'),
                    'label':    field.get('label'),
                    'response': self.payload.get(field['cid'])
                })
        return payload

    @property
    def repr(self):
        doc = {
            'id':           str(self),
            'acquired':     str(self.acquired),
            'flagged':      self.flagged,
            'survey':       str(self.survey),
            'root':         self.survey.resolved_root.tiny_repr,
            'response':     str(self.response),
            'payload':      self.resolved_payload,
            'type':         self.__class__.__name__,
        }
        return doc

class SurveyTicket(Notification):
    origin          = db.ReferenceField(User)
    survey          = db.ReferenceField(Survey, required = True)
    completed       = db.BooleanField(default = False)
    complete_time   = db.DateTimeField()

    @property
    def repr(self):
        doc = {
            'id':               str(self),
            'acquired':         str(self.acquired),
            'flagged':          self.flagged,
            'survey':           str(self.survey),
            'origin':           self.origin.repr,
            'targets':          self.destined.repr,
            'completed':        self.completed,
            'complete_time':    str(self.complete_time),
            'payload':          self.payload,
            'type':             self.__class__.__name__,
        }
        return doc
