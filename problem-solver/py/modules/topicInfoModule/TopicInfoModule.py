from sc_kpm import ScModule
from .TopicInfoAgent import TopicInfoAgent


class TopicInfoModule(ScModule):
    def __init__(self):
        super().__init__(TopicInfoAgent())
