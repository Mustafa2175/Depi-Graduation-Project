select
    l.location_key,
    l.location_city as city,
    l.location_gov  as governorate,
    g.region
from {{ source('warehouse', 'dim_location') }} l
left join {{ source('warehouse', 'ref_governorate') }} g
    on l.location_gov = g.governorate
