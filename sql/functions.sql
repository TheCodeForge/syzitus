CREATE OR REPLACE FUNCTION public.age(boards)
 RETURNS integer
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$

      SELECT CAST( EXTRACT( EPOCH FROM CURRENT_TIMESTAMP) AS int) - $1.created_utc
      $function$
;

CREATE OR REPLACE FUNCTION public.age(comments)
 RETURNS integer
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
      SELECT CAST( EXTRACT( EPOCH FROM CURRENT_TIMESTAMP) AS int) - $1.created_utc
      $function$
;

CREATE OR REPLACE FUNCTION public.age(submissions)
 RETURNS integer
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
      SELECT CAST( EXTRACT( EPOCH FROM CURRENT_TIMESTAMP) AS int) - $1.created_utc
      $function$
;

CREATE OR REPLACE FUNCTION public.avg_score_computed(boards)
 RETURNS numeric
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
select coalesce (
    (select avg(score_top) from submissions
    where original_board_id=$1.id
    and score_top>0)
    ,
    1
    )
$function$
;

CREATE OR REPLACE FUNCTION public.board_id(comments)
 RETURNS integer
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
      SELECT submissions.board_id
      FROM submissions
      WHERE submissions.id=$1.parent_submission
      $function$
;

CREATE OR REPLACE FUNCTION public.board_id(reports)
 RETURNS integer
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
      SELECT submissions.board_id
      FROM submissions
      WHERE submissions.id=$1.post_id
      $function$
;

CREATE OR REPLACE FUNCTION public.comment_count(submissions)
 RETURNS bigint
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
      SELECT COUNT(*)
      FROM comments
      WHERE is_banned=false
        AND deleted_utc=0
        AND parent_submission = $1.id
      $function$
;

CREATE OR REPLACE FUNCTION public.comment_energy(users)
 RETURNS bigint
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
     SELECT COALESCE(
     (
      SELECT SUM(comments.score_top)
      FROM comments
      WHERE comments.author_id=$1.id
        AND comments.is_banned=false
        and comments.parent_submission is not null
      ),
      0
      )
    $function$
;

CREATE OR REPLACE FUNCTION public.created_utc(notifications)
 RETURNS integer
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
select created_utc from comments
where comments.id=$1.comment_id
$function$
;

CREATE OR REPLACE FUNCTION public.downs(comments)
 RETURNS bigint
 LANGUAGE sql
AS $function$
select (
(
  SELECT count(*)
  from (
    select * from commentvotes
    where comment_id=$1.id
    and vote_type=-1
    and user_id not in
    (
        select user_id
        from bans
        where board_id=$1.original_board_id
        and is_active=true
    )
  ) as v1
   join (select * from users where users.is_banned=0 or users.unban_utc>0
) as u0
    on u0.id=v1.user_id
)-(
  SELECT count(distinct v1.id)
  from (
    select * from commentvotes
    where comment_id=$1.id
    and vote_type=-1
    and user_id not in
    (
        select user_id
        from bans
        where board_id=$1.original_board_id
        and is_active=true
    )
  ) as v1
   join (select * from users where is_banned=0 or users.unban_utc>0) as u1
    on u1.id=v1.user_id
   join (select * from alts) as a
    on (a.user1=v1.user_id or a.user2=v1.user_id)
   join (
      select * from commentvotes
      where comment_id=$1.id
      and vote_type=-1
    and user_id not in
    (
        select user_id
        from bans
        where board_id=$1.original_board_id
        and is_active=true
    )
  ) as v2
    on ((a.user1=v2.user_id or a.user2=v2.user_id) and v2.id != v1.id)
   join (select * from users where is_banned=0 or users.unban_utc>0) as u2
    on u2.id=v2.user_id
  where v1.id is not null
  and v2.id is not null
))
     $function$
;

CREATE OR REPLACE FUNCTION public.downs(submissions)
 RETURNS bigint
 LANGUAGE sql
AS $function$
select (
(
  SELECT count(*)
  from (
    select * from votes
    where submission_id=$1.id
    and vote_type=-1
    and user_id not in
    (
        select user_id
        from bans
        where board_id=$1.board_id
        and is_active=true
    )
  ) as v1
   join (select * from users where users.is_banned=0 or users.unban_utc>0) as u0
    on u0.id=v1.user_id
)-(
  SELECT count(distinct v1.id)
  from (
    select * from votes
    where submission_id=$1.id
    and vote_type=-1
    and user_id not in
    (
        select user_id
        from bans
        where board_id=$1.board_id
        and is_active=true
    )
  ) as v1
   join (select * from users where is_banned=0 or users.unban_utc>0) as u1
    on u1.id=v1.user_id
   join (select * from alts) as a
    on (a.user1=v1.user_id or a.user2=v1.user_id)
   join (
      select * from votes
      where submission_id=$1.id
      and vote_type=-1
    and user_id not in
    (
        select user_id
        from bans
        where board_id=$1.board_id
        and is_active=true
    )
  ) as v2
    on ((a.user1=v2.user_id or a.user2=v2.user_id) and v2.id != v1.id)
   join (select * from users where is_banned=0 or users.unban_utc>0) as u2
    on u2.id=v2.user_id
  where v1.id is not null
  and v2.id is not null
))
     $function$
;

CREATE OR REPLACE FUNCTION public.energy(users)
 RETURNS bigint
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
     SELECT COALESCE(
     (
      SELECT SUM(submissions.score_top)
      FROM submissions
      WHERE submissions.author_id=$1.id
        AND submissions.is_banned=false
      ),
      0
      )
    $function$
;

CREATE OR REPLACE FUNCTION public.flag_count(comments)
 RETURNS bigint
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
      SELECT COUNT(*)
      FROM commentflags
      JOIN users ON commentflags.user_id=users.id
      WHERE comment_id=$1.id
      AND users.is_banned=0
      $function$
;

CREATE OR REPLACE FUNCTION public.flag_count(submissions)
 RETURNS bigint
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
      SELECT COUNT(*)
      FROM flags
      JOIN users ON flags.user_id=users.id
      WHERE post_id=$1.id
      AND users.is_banned=0
      $function$
;

CREATE OR REPLACE FUNCTION public.follower_count(users)
 RETURNS bigint
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
    select (
         (select count(*)
         from follows
         left join users
         on follows.user_id=users.id
         where follows.target_id=$1.id
         and (users.is_banned=0 or users.created_utc>0)
         and users.is_deleted=false
         )-(
             select count(distinct f1.id)
                from
                (
                    select *
                    from follows
                    where target_id=$1.id
                ) as f1
                join (select * from users where is_banned=0 or unban_utc>0) as u1
                 on u1.id=f1.user_id
                join (select * from alts) as a
                 on (a.user1=f1.user_id or a.user2=f1.user_id)
                join (
                    select *
                    from follows
                    where target_id=$1.id
                ) as f2
                on ((a.user1=f2.user_id or a.user2=f2.user_id) and f2.id != f1.id)
                join (select * from users where is_banned=0 or unban_utc>0) as u2
                 on u2.id=f2.user_id
                where f1.id is not null
                and f2.id is not null           
             )
         
         
         
         )
        $function$
;

CREATE OR REPLACE FUNCTION public.is_banned(notifications)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
select is_banned from comments
where comments.id=$1.comment_id
$function$
;

CREATE OR REPLACE FUNCTION public.is_public(comments)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
      SELECT submissions.is_public
      FROM submissions
      WHERE submissions.id=$1.parent_submission
      $function$
;

CREATE OR REPLACE FUNCTION public.is_public(submissions)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
select
    case
        when $1.post_public=true
            then true
        when (select (is_private)
            from boards
            where id=$1.board_id
            )=true
            then false
        else
            true
    end
     
      $function$
;

CREATE OR REPLACE FUNCTION public.mod_count(users)
 RETURNS bigint
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$select count(*) from mods where accepted=true and invite_rescinded=false and user_id=$1.id;$function$
;

CREATE OR REPLACE FUNCTION public.rank_activity(submissions)
 RETURNS double precision
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
      SELECT 1000000.0*CAST($1.comment_count AS float)/((CAST(($1.age+5000) AS FLOAT)/100.0)^(1.35))
    $function$
;

CREATE OR REPLACE FUNCTION public.rank_best(submissions)
 RETURNS double precision
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
      SELECT 10000000.0*CAST(($1.upvotes - $1.downvotes + 1) AS float)/((CAST(($1.age+3600) AS FLOAT)*cast((select boards.subscriber_count from boards where boards.id=$1.board_id)+10000 as float)/1000.0)^(1.35))
      $function$
;

CREATE OR REPLACE FUNCTION public.rank_fiery(comments)
 RETURNS double precision
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
  SELECT SQRT(CAST(($1.upvotes * $1.downvotes) AS float))/((CAST(($1.age+100000) AS FLOAT)/6.0)^(1.5))
  $function$
;

CREATE OR REPLACE FUNCTION public.rank_fiery(submissions)
 RETURNS double precision
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
      SELECT 1000000.0*SQRT(CAST(($1.upvotes * $1.downvotes) AS float))/((CAST(($1.age+5000) AS FLOAT)/100.0)^(1.35))
      $function$
;

CREATE OR REPLACE FUNCTION public.rank_hot(comments)
 RETURNS double precision
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
  SELECT CAST(($1.upvotes - $1.downvotes) AS float)/((CAST(($1.age+100000) AS FLOAT)/6.0)^(1.5))
  $function$
;

CREATE OR REPLACE FUNCTION public.rank_hot(submissions)
 RETURNS double precision
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
      SELECT 1000000.0*CAST(($1.upvotes - $1.downvotes) AS float)/((CAST(($1.age+5000) AS FLOAT)/100.0)^(1.5))
      $function$
;

CREATE OR REPLACE FUNCTION public.recent_subscriptions(boards)
 RETURNS bigint
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
         select count(*)
         from subscriptions
         left join users
         on subscriptions.user_id=users.id
         where subscriptions.board_id=$1.id
         and subscriptions.is_active=true
         and subscriptions.created_utc > CAST( EXTRACT( EPOCH FROM CURRENT_TIMESTAMP) AS int) - 60*60*24
         and users.is_banned=0
        $function$
;

CREATE OR REPLACE FUNCTION public.referral_count(users)
 RETURNS bigint
 LANGUAGE sql
 STABLE STRICT
AS $function$
        SELECT COUNT(*)
        FROM USERS
        WHERE users.is_banned=0
        AND users.referred_by=$1.id
    $function$
;

CREATE OR REPLACE FUNCTION public.report_count(submissions)
 RETURNS bigint
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
      SELECT COUNT(*)
      FROM reports
      JOIN users ON reports.user_id=users.id
      WHERE post_id=$1.id
      AND users.is_banned=0
      and reports.created_utc >= $1.edited_utc
      $function$
;

CREATE OR REPLACE FUNCTION public.score(comments)
 RETURNS integer
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
      SELECT ($1.upvotes - $1.downvotes)
      $function$
;

CREATE OR REPLACE FUNCTION public.score(submissions)
 RETURNS integer
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
      SELECT ($1.upvotes - $1.downvotes)
      $function$
;

CREATE OR REPLACE FUNCTION public.subscriber_count(boards)
 RETURNS bigint
 LANGUAGE sql
 IMMUTABLE STRICT
AS $function$
    select
        case 
        when $1.is_private=false
        then
             (
             (
                 select count(*)
                 from subscriptions
                 left join users
                 on subscriptions.user_id=users.id
                 where subscriptions.board_id=$1.id
                 and subscriptions.is_active=true
                 and users.is_deleted=false and (users.is_banned=0 or users.unban_utc>0)
             )-(
                select count(distinct s1.id)
                from
                (
                    select *
                    from subscriptions
                    where board_id=$1.id
                    and is_active=true
                ) as s1
                join (select * from users where is_banned=0 or unban_utc>0) as u1
                 on u1.id=s1.user_id
                join (select * from alts) as a
                 on (a.user1=s1.user_id or a.user2=s1.user_id)
                join (
                    select *
                    from subscriptions
                    where board_id=$1.id
                    and is_active=true
                ) as s2
                on ((a.user1=s2.user_id or a.user2=s2.user_id) and s2.id != s1.id)
                join (select * from users where is_banned=0 or unban_utc>0) as u2
                 on u2.id=s2.user_id
                where s1.id is not null
                and s2.id is not null           
             )
             )
        when $1.is_private=true
        then
             (
             (
             select count(*)
             from subscriptions
             left join users
                on subscriptions.user_id=users.id
             left join (
                select * from contributors
                where contributors.board_id=$1.id
             )as contribs
                on contribs.user_id=users.id
             left join (
                select * from mods
                where mods.board_id=$1.id
                and accepted=true
             )as m
                on m.user_id=users.id
             where subscriptions.board_id=$1.id
             and subscriptions.is_active=true
             and users.is_deleted=false and (users.is_banned=0 or users.unban_utc>0)
             and (contribs.user_id is not null or m.id is not null)
             )
             )
        end     
$function$
;

CREATE OR REPLACE FUNCTION public.ups(comments)
 RETURNS bigint
 LANGUAGE sql
AS $function$
select (
(
  SELECT count(*)
  from (
    select * from commentvotes
    where comment_id=$1.id
    and vote_type=1
    and user_id not in
    (
        select user_id
        from bans
        where board_id=$1.original_board_id
        and is_active=true
    )
  ) as v1
   join (select * from users where users.is_banned=0 or users.unban_utc>0) as u0
    on u0.id=v1.user_id
)-(
  SELECT count(distinct v1.id)
  from (
    select * from commentvotes
    where comment_id=$1.id
    and vote_type=1
    and user_id not in
    (
        select user_id
        from bans
        where board_id=$1.original_board_id
        and is_active=true
    )
  ) as v1
   join (select * from users where is_banned=0 or users.unban_utc>0) as u1
    on u1.id=v1.user_id
   join (select * from alts) as a
    on (a.user1=v1.user_id or a.user2=v1.user_id)
   join (
      select * from commentvotes
      where comment_id=$1.id
      and vote_type=1
        and user_id not in
        (
            select user_id
            from bans
            where board_id=$1.original_board_id
            and is_active=true
        )
  ) as v2
    on ((a.user1=v2.user_id or a.user2=v2.user_id) and v2.id != v1.id)
   join (select * from users where is_banned=0 or users.unban_utc>0) as u2
    on u2.id=v2.user_id
  where v1.id is not null
  and v2.id is not null
))
     $function$
;

CREATE OR REPLACE FUNCTION public.ups(submissions)
 RETURNS bigint
 LANGUAGE sql
AS $function$
select (
(
  SELECT count(*)
  from (
    select * from votes
    where submission_id=$1.id
    and vote_type=1
    and user_id not in
    (
        select user_id
        from bans
        where board_id=$1.board_id
        and is_active=true
    )
  ) as v1
   join (select * from users where users.is_banned=0 or users.unban_utc>0) as u0
    on u0.id=v1.user_id
)-(
  SELECT count(distinct v1.id)
  from (
    select * from votes
    where submission_id=$1.id
    and vote_type=1
    and user_id not in
    (
        select user_id
        from bans
        where board_id=$1.board_id
        and is_active=true
    )
  ) as v1
   join (select * from users where is_banned=0 or users.unban_utc>0) as u1
    on u1.id=v1.user_id
   join (select * from alts) as a
    on (a.user1=v1.user_id or a.user2=v1.user_id)
   join (
      select * from votes
      where submission_id=$1.id
      and vote_type=1
    and user_id not in
    (
        select user_id
        from bans
        where board_id=$1.board_id
        and is_active=true
    )
  ) as v2
    on ((a.user1=v2.user_id or a.user2=v2.user_id) and v2.id != v1.id)
   join (select * from users where is_banned=0 or users.unban_utc>0) as u2
    on u2.id=v2.user_id
  where v1.id is not null
  and v2.id is not null
))
     $function$
;
