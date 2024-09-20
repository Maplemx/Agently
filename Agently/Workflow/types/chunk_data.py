from typing import TypeAlias, Dict, List, TypedDict, Literal


class ChunkDepData(TypedDict):
  handle: str
  data_slots: List[Dict]

class ChunkData(TypedDict):
  id: str
  loop_entry: bool
  type: Literal['Normal', 'Loop', 'Start', 'End']
  executor: callable
  deps: List[ChunkDepData]