"""
Module for text generating
"""

import os.path
import random
import re
from typing import Dict, List, Set

from nltk.tokenize import sent_tokenize, word_tokenize

BASE_PATH = os.path.join('data', 'text', 'speech_base.txt')

PARTS_OF_SPEECH = {
        'noun': 'S',
        'verb': 'V',
        'personal pronoun': 'S-PRO',
        'connecting words': 'CONJ',
        'other': 'NONLEX'
    }


class TextGenerator:
    def __init__(self, base_path: str):
        """
        :param base_path: path to base text
        """

        with open(base_path, 'r') as base:
            sentences = sent_tokenize(base.read())

        self.words: Set[str] = set()
        self.ends: Set[str] = set()
        self.links: Dict[str, List[str]] = dict()
        self.max_sent_length = -1
        for sentence in sentences:
            words = word_tokenize(sentence)
            self.max_sent_length = len(words) if len(words) > self.max_sent_length else self.max_sent_length
            self.ends.add(words[-1])
            for i, word in enumerate(words):
                self.words.add(word)
                if i < len(words) - 1:
                    self.links[words[i]] = self.links.get(words[i], list()) + [words[i + 1]]

    @staticmethod
    def _polish_text(text: str) -> str:
        spaces = re.findall(' [' + re.escape("'!#$%&)*+,./:;>?@\\]^_|}~") + ']|[' + re.escape('(<?@[`{') + '] ', text)
        result = text
        for sp in spaces:
            result = result.replace(sp, sp.replace(' ', ''))

        result = result[0].upper() + result.lstrip(result[0])

        return result

    def generate(self) -> Set[str]:
        """
        Generates texts
        :return: unique texts
        """
        variants_stack = list()
        for i in range(0, 10):
            variants_stack.append(random.choices(list(self.words)))
        result = set()

        end_regex = '^[а-яА-Я].*(' + '|'.join(list(map(re.escape, self.ends))) + ")$"

        while variants_stack and len(result) < 20:
            random.shuffle(variants_stack)
            popped = variants_stack.pop()
            joined = ' '.join(popped)
            if len(popped) < self.max_sent_length:

                ends = self.links.get(popped[-1], list())
                random.shuffle(ends)
                for end in ends:
                    if end not in popped:
                        variants_stack.append(popped + [end])

                if re.search(end_regex, joined):
                    result.add(self._polish_text(joined))

        return result


def main():
    text_gen = TextGenerator(BASE_PATH)
    for text in text_gen.generate():
        print(text)


if __name__ == '__main__':
    main()