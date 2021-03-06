"""Module for operating on telegram messages"""

from typing import Set

from telebot.types import Message

import logger

LOGGER = logger.get_logger(__file__)
CURRENT_GRADING_MESSAGE = None


class GradableMessage:
    """
    For storing information about grading message which is used for agent learning
    """

    # attribute that represents 'grade' of the reply on message
    # based on ratio of likes and dislikes
    _grade: int = 0

    # 1 if grade was increased -1 otherwise
    _change_difference: [-1, 1] = 0

    _likes_num: int = 0
    _dislikes_num: int = 0

    def __init__(self, message: Message, input_message: str):
        self._users_liked: Set[int] = set()
        self._users_disliked: Set[int] = set()
        # message that bot sent
        self.message = message
        self.reply_message = message.text
        # message that bot received
        self.input_message = input_message

    def _update_likes_num(self, user_id):
        if user_id in self._users_liked:
            self._likes_num -= 1
            self._users_liked.remove(user_id)
        else:
            self._likes_num += 1
            self._users_liked.add(user_id)
            if user_id in self._users_disliked:
                self._update_dislikes_num(user_id)

    def _update_dislikes_num(self, user_id):
        if user_id in self._users_disliked:
            self._dislikes_num -= 1
            self._users_disliked.remove(user_id)
        else:
            self._dislikes_num += 1
            self._users_disliked.add(user_id)
            if user_id in self._users_liked:
                self._update_likes_num(user_id)

    def update_grade(self) -> bool:
        """
        Updates grade of the message
        :return: True if the grade was changed else False
        """
        old_grade = self._grade
        self._grade = self._likes_num - self._dislikes_num

        self._change_difference = self._grade - old_grade

        return self._change_difference != 0

    def up_vote(self, user_id: int) -> None:
        """
        Handles up-voting action made by a user
        :param user_id: id of a voted user
        :return: None
        """
        self._update_likes_num(user_id)

    def down_vote(self, user_id: int) -> None:
        """
        Handles down-voting action made by a user
        :param user_id: id of a voted user
        :return: None
        """
        self._update_dislikes_num(user_id)

    def get_likes_num(self) -> int:
        """
        Gets number of likes
        :return: number of likes
        """
        return self._likes_num

    def get_dislikes_num(self) -> int:
        """
        Gets number of dislikes
        :return: number of dislikes
        """
        return self._dislikes_num

    def get_grade(self) -> int:
        """
        Gets the grade of the message
        :return: grade
        """
        return self._grade

    def get_change_difference(self) -> int:
        """
        Gets change sign
        :return: change sign
        """
        return self._change_difference
