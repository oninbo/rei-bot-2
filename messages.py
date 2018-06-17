"""Module for operating on telegram messages"""

from typing import Set
from telebot.types import Message
import logger

LOGGER = logger.get_logger(__file__)


class GradableMessage:
    """
    For storing information about grading message which is used for agent learning
    """

    # attribute that represents 'grade' of the reply on message based on ratio of likes and dislikes
    # where -1 is for dislikes > likes 0 is for equality and 1 is for likes > dislikes
    _grade: [-1, 0, 1] = 0

    _likes: int >= 0 = 0
    _dislikes: int >= 0 = 0

    _liked: Set[int] = set()
    _disliked: Set[int] = set()

    def __init__(self, message: Message, reply_message: str):
        self.message = message
        self.input_message = message.text
        self.reply_message = reply_message

    def _update_likes(self, user_id):
        if user_id in self._liked:
            self._likes -= 1
            self._liked.remove(user_id)
        else:
            self._likes += 1
            self._liked.add(user_id)

    def _update_dislikes(self, user_id):
        if user_id in self._disliked:
            self._dislikes -= 1
            self._disliked.remove(user_id)
        else:
            self._dislikes += 1
            self._disliked.add(user_id)

    def update_grade(self) -> bool:
        old_grade = self._grade
        if self._likes > self._dislikes:
            self._grade = 1
        elif self._likes < self._dislikes:
            self._grade = -1
        else:
            self._grade = 0

        if self._grade != old_grade:
            return True
        else:
            return False

    def up_vote(self, user_id):
        self._update_likes(user_id)

    def down_vote(self, user_id):
        self._update_dislikes(user_id)

    def get_likes(self):
        return self._likes

    def get_dislikes(self):
        return self._dislikes

    def get_grade(self):
        return self._grade


CURRENT_GRADING_MESSAGE = None
