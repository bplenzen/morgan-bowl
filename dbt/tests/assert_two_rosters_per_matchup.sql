select
  week,
  matchup_id,
  count(*) as roster_count
from {{ ref('stg_matchups') }}
group by 1, 2
having count(*) <> 2
