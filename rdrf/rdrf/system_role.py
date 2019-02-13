from enum import Enum

class SystemRoles(Enum):
    CIC_DEV = 'CIC_DEV'
    CIC_PROMS = 'CIC_PROMS'
    CIC_CLINICAL = 'CIC_CLINICAL'
    NORMAL = 'NORMAL'

    @classmethod
    def proms_role(cls):
        # cls here is the enumeration
        return cls.CIC_PROMS
    
    @classmethod
    def dev_role(cls):
        return cls.CIC_DEV
    
    @classmethod
    def normal_role(cls):
        return cls.NORMAL
    
    @classmethod
    def cic_clinical_role(cls):
        return cls.CIC_CLINICAL

    @classmethod
    def has_value(cls, value):
        return any(value == item.value for item in cls)

    @classmethod
    def from_value(cls, value):
      try:
        return {item.value: item for item in cls}[value]
      except KeyError:
        return 'ERROR: Invalid System Role!'