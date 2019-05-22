class SystemRoles:
    CIC_DEV = 'CIC_DEV'
    CIC_PROMS = 'CIC_PROMS'
    CIC_CLINICAL = 'CIC_CLINICAL'
    NORMAL = 'NORMAL'

    @staticmethod
    def get_role(env):
        sr = env.get("SYSTEM_ROLE", "NORMAL")
        if sr == "NORMAL":
            return SystemRoles.NORMAL
        else:
            if sr not in [SystemRoles.CIC_DEV,
                          SystemRoles.CIC_PROMS,
                          SystemRoles.CIC_CLINICAL,
                          SystemRoles.NORMAL]:
                raise Exception("Invalid System Role: %s" % sr)
            else:
                return sr
