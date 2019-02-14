from enum import Enum

class SystemRoles(Enum):
    CIC_DEV = 'CIC_DEV'
    CIC_PROMS = 'CIC_PROMS'
    CIC_CLINICAL = 'CIC_CLINICAL'
    NORMAL = 'NORMAL'

    @classmethod
    def from_value(cls, value):
      try:
        return {item.value: item for item in cls}[value]
      except KeyError:
        raise Exception("Invalid SYSTEM_ROLE : %s, allowed values are CIC_CLINICAL, CIC_DEV, CIC_PROMS and NORMAL" % value)
