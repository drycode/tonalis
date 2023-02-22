from music_dsl.domain.time import TimeSignature


class Measure:
    def __init__(self, m_number: int, time_signature: TimeSignature):
        self.m_number = m_number
        self.time_signature = time_signature
        self.beat_containers = [None] * time_signature.denominator
