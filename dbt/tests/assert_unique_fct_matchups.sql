select
  week,
  matchup_id,
  roster_id
from {{ ref('fct_matchups') }}
group by 1, 2, 3
having count(*) > 1
