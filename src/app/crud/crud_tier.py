from fastcrud import FastCRUD

from ..models.course import Tier
from ..schemas.tier import TierCreateInternal, TierDelete, TierRead, TierUpdate, TierUpdateInternal

CRUDTier = FastCRUD[Tier, TierCreateInternal, TierUpdate, TierUpdateInternal, TierDelete, TierRead]
crud_tiers = CRUDTier(Tier)
