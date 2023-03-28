-- public.badlinks definition

-- Drop table

-- DROP TABLE public.badlinks;

CREATE TABLE public.badlinks (
    id serial4 NOT NULL,
    reason int4 NULL,
    link varchar(512) NULL,
    autoban bool NULL,
    CONSTRAINT badlinks_pkey PRIMARY KEY (id)
);


-- public.badpics definition

-- Drop table

-- DROP TABLE public.badpics;

CREATE TABLE public.badpics (
    id bigserial NOT NULL,
    description varchar(255) NULL,
    phash varchar(64) NULL,
    ban_reason varchar(64) NULL,
    ban_time int4 NULL,
    CONSTRAINT badpics_pkey PRIMARY KEY (id)
);
CREATE INDEX badpics_phash_trgm_idx ON public.badpics USING gin (phash gin_trgm_ops);
CREATE INDEX ix_badpics_phash ON public.badpics USING btree (phash);


-- public.badwords definition

-- Drop table

-- DROP TABLE public.badwords;

CREATE TABLE public.badwords (
    id serial4 NOT NULL,
    keyword varchar(64) NULL,
    regex varchar(256) NULL,
    CONSTRAINT badwords_pkey PRIMARY KEY (id)
);


-- public.domains definition

-- Drop table

-- DROP TABLE public.domains;

CREATE TABLE public.domains (
    id serial4 NOT NULL,
    "domain" varchar NULL,
    reason int4 NULL,
    show_thumbnail bool NULL,
    embed_function varchar(64) NULL,
    embed_template varchar(32) NULL,
    is_banned bool NOT NULL,
    CONSTRAINT domains_pkey PRIMARY KEY (id)
);
CREATE INDEX ix_domains_domain ON public.domains USING btree (domain);


-- public.promocodes definition

-- Drop table

-- DROP TABLE public.promocodes;

CREATE TABLE public.promocodes (
    id serial4 NOT NULL,
    code varchar(64) NULL,
    is_active bool NULL,
    percent_off int4 NULL,
    flat_cents_off int4 NULL,
    flat_cents_min int4 NULL,
    promo_start_utc int4 NULL,
    promo_end_utc int4 NULL,
    promo_info varchar(64) NULL,
    CONSTRAINT promocodes_pkey PRIMARY KEY (id)
);


-- public.users definition

-- Drop table

-- DROP TABLE public.users;

CREATE TABLE public.users (
    id serial4 NOT NULL,
    username varchar NULL,
    email varchar NULL,
    passhash varchar NULL,
    created_utc int4 NULL,
    admin_level int4 NULL,
    is_activated bool NULL,
    over_18 bool NULL,
    creation_ip varchar NULL,
    bio varchar NULL,
    bio_html varchar NULL,
    real_id varchar NULL,
    referred_by int4 NULL,
    is_banned int4 NULL,
    ban_reason varchar NULL,
    defaultsorting varchar NULL,
    defaulttime varchar NULL,
    login_nonce int4 NULL,
    title_id int4 NULL,
    has_profile bool NULL,
    has_banner bool NULL,
    reserved varchar(256) NULL,
    is_nsfw bool NULL,
    profile_nonce int4 NULL,
    banner_nonce int4 NULL,
    last_siege_utc int4 NULL,
    mfa_secret varchar(64) NULL,
    hide_offensive bool NULL,
    hide_bot bool NULL,
    show_nsfl bool NULL,
    is_private bool NULL,
    unban_utc int4 NULL,
    is_deleted bool NULL,
    delete_reason varchar(500) NULL,
    filter_nsfw bool NULL,
    stored_karma int4 NULL,
    stored_subscriber_count int4 NULL,
    coin_balance int4 NULL,
    premium_expires_utc int4 NULL,
    negative_balance_cents int4 NULL,
    is_nofollow bool NULL,
    custom_filter_list varchar(1000) NULL,
    discord_id varchar(64) NULL,
    creation_region varchar(2) NULL,
    ban_evade int4 NULL,
    profile_upload_ip varchar(255) NULL,
    banner_upload_ip varchar(255) NULL,
    profile_upload_region varchar(2) NULL,
    banner_upload_region varchar(2) NULL,
    original_username varchar(255) NULL,
    name_changed_utc int4 NULL,
    CONSTRAINT users_pkey PRIMARY KEY (id)
);
CREATE INDEX users_created_utc_idx ON public.users USING btree (created_utc DESC);
CREATE INDEX users_email_trgm_idx ON public.users USING gin (email gin_trgm_ops);
CREATE INDEX users_original_username_trgm_idx ON public.users USING gin (original_username gin_trgm_ops);
CREATE INDEX users_username_trgm_idx ON public.users USING gin (username gin_trgm_ops);


-- public.alts definition

-- Drop table

-- DROP TABLE public.alts;

CREATE TABLE public.alts (
    id serial4 NOT NULL,
    user1 int4 NULL,
    user2 int4 NULL,
    is_manual bool NULL,
    CONSTRAINT alts_pkey PRIMARY KEY (id),
    CONSTRAINT alts_user1_fkey FOREIGN KEY (user1) REFERENCES public.users(id),
    CONSTRAINT alts_user2_fkey FOREIGN KEY (user2) REFERENCES public.users(id)
);
CREATE INDEX ix_alts_user1 ON public.alts USING btree (user1);
CREATE INDEX ix_alts_user2 ON public.alts USING btree (user2);


-- public.badges definition

-- Drop table

-- DROP TABLE public.badges;

CREATE TABLE public.badges (
    id serial4 NOT NULL,
    user_id int4 NULL,
    badge_id int4 NULL,
    description varchar(64) NULL,
    url varchar(256) NULL,
    created_utc int4 NULL,
    CONSTRAINT badges_pkey PRIMARY KEY (id),
    CONSTRAINT badges_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);


-- public.boards definition

-- Drop table

-- DROP TABLE public.boards;

CREATE TABLE public.boards (
    id serial4 NOT NULL,
    "name" varchar NULL,
    created_utc int4 NULL,
    description varchar NULL,
    description_html varchar NULL,
    over_18 bool NULL,
    is_nsfl bool NULL,
    is_banned bool NULL,
    has_banner bool NULL,
    has_profile bool NULL,
    creator_id int4 NULL,
    ban_reason varchar(256) NULL,
    color varchar(8) NULL,
    restricted_posting bool NULL,
    disallowbots bool NULL,
    profile_nonce int4 NULL,
    banner_nonce int4 NULL,
    is_private bool NULL,
    rank_trending float8 NULL,
    stored_subscriber_count int4 NOT NULL,
    all_opt_out bool NULL,
    is_siegable bool NULL,
    is_locked_category bool NULL,
    css_nonce int4 NULL,
    css varchar(65536) NOT NULL,
    trending_rank float8 NULL,
    subcat_id int4 NULL,
    is_locked bool NULL,
    CONSTRAINT boards_pkey PRIMARY KEY (id),
    CONSTRAINT boards_creator_id_fkey FOREIGN KEY (creator_id) REFERENCES public.users(id)
);
CREATE INDEX boards_name_trgm_idx ON public.boards USING gin (name gin_trgm_ops);
CREATE INDEX boards_rank_trending_idx ON public.boards USING btree (rank_trending DESC);
CREATE INDEX boards_stored_subscriber_idx ON public.boards USING btree (stored_subscriber_count DESC);


-- public.contributors definition

-- Drop table

-- DROP TABLE public.contributors;

CREATE TABLE public.contributors (
    id bigserial NOT NULL,
    user_id int4 NULL,
    board_id int4 NULL,
    created_utc int8 NULL,
    is_active bool NULL,
    approving_mod_id int4 NULL,
    CONSTRAINT contributors_pkey PRIMARY KEY (id),
    CONSTRAINT contributors_approving_mod_id_fkey FOREIGN KEY (approving_mod_id) REFERENCES public.users(id),
    CONSTRAINT contributors_board_id_fkey FOREIGN KEY (board_id) REFERENCES public.boards(id),
    CONSTRAINT contributors_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);


-- public.follows definition

-- Drop table

-- DROP TABLE public.follows;

CREATE TABLE public.follows (
    id bigserial NOT NULL,
    user_id int8 NULL,
    target_id int8 NULL,
    created_utc int8 NULL,
    get_notifs bool NULL,
    CONSTRAINT follows_pkey PRIMARY KEY (id),
    CONSTRAINT follows_target_id_fkey FOREIGN KEY (target_id) REFERENCES public.users(id),
    CONSTRAINT follows_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE INDEX ix_follows_target_id ON public.follows USING btree (target_id);
CREATE INDEX ix_follows_user_id ON public.follows USING btree (user_id);


-- public.ips definition

-- Drop table

-- DROP TABLE public.ips;

CREATE TABLE public.ips (
    id serial4 NOT NULL,
    addr varchar(64) NULL,
    reason varchar(256) NULL,
    banned_by int4 NULL,
    unban_utc int4 NULL,
    CONSTRAINT ips_pkey PRIMARY KEY (id),
    CONSTRAINT ips_banned_by_fkey FOREIGN KEY (banned_by) REFERENCES public.users(id)
);
CREATE UNIQUE INDEX ix_ips_addr ON public.ips USING btree (addr);


-- public.mods definition

-- Drop table

-- DROP TABLE public.mods;

CREATE TABLE public.mods (
    id bigserial NOT NULL,
    user_id int4 NULL,
    board_id int4 NULL,
    created_utc int4 NULL,
    accepted bool NULL,
    invite_rescinded bool NULL,
    perm_content bool NULL,
    perm_appearance bool NULL,
    perm_config bool NULL,
    perm_access bool NULL,
    perm_full bool NULL,
    CONSTRAINT mods_pkey PRIMARY KEY (id),
    CONSTRAINT mods_board_id_fkey FOREIGN KEY (board_id) REFERENCES public.boards(id),
    CONSTRAINT mods_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE INDEX ix_mods_board_id ON public.mods USING btree (board_id);
CREATE INDEX ix_mods_user_id ON public.mods USING btree (user_id);


-- public.oauth_apps definition

-- Drop table

-- DROP TABLE public.oauth_apps;

CREATE TABLE public.oauth_apps (
    id serial4 NOT NULL,
    client_id varchar(64) NULL,
    client_secret varchar(128) NULL,
    app_name varchar(50) NULL,
    redirect_uri varchar(4096) NULL,
    author_id int4 NULL,
    is_banned bool NULL,
    description varchar(256) NULL,
    CONSTRAINT oauth_apps_pkey PRIMARY KEY (id),
    CONSTRAINT oauth_apps_author_id_fkey FOREIGN KEY (author_id) REFERENCES public.users(id)
);


-- public.paypal_txns definition

-- Drop table

-- DROP TABLE public.paypal_txns;

CREATE TABLE public.paypal_txns (
    id serial4 NOT NULL,
    user_id int4 NULL,
    created_utc int4 NULL,
    paypal_id varchar NULL,
    usd_cents int4 NULL,
    coin_count int4 NULL,
    promo_id int4 NULL,
    status int4 NULL,
    CONSTRAINT paypal_txns_pkey PRIMARY KEY (id),
    CONSTRAINT paypal_txns_promo_id_fkey FOREIGN KEY (promo_id) REFERENCES public.promocodes(id),
    CONSTRAINT paypal_txns_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);


-- public.submissions definition

-- Drop table

-- DROP TABLE public.submissions;

CREATE TABLE public.submissions (
    id bigserial NOT NULL,
    author_id int8 NULL,
    repost_id int8 NULL,
    edited_utc int8 NULL,
    created_utc int8 NULL,
    is_banned bool NULL,
    deleted_utc int4 NULL,
    purged_utc int4 NULL,
    distinguish_level int4 NULL,
    gm_distinguish int4 NULL,
    created_str varchar(255) NULL,
    stickied bool NULL,
    domain_ref int4 NULL,
    is_approved int4 NULL,
    approved_utc int4 NULL,
    board_id int4 NULL,
    original_board_id int4 NULL,
    over_18 bool NULL,
    creation_ip varchar(64) NULL,
    mod_approved int4 NULL,
    accepted_utc int4 NULL,
    has_thumb bool NULL,
    post_public bool NULL,
    score_hot float8 NULL,
    score_disputed float8 NULL,
    score_top float8 NULL,
    score_activity float8 NULL,
    is_offensive bool NULL,
    is_nsfl bool NULL,
    is_pinned bool NULL,
    score_best float8 NULL,
    is_bot bool NULL,
    upvotes int4 NOT NULL,
    downvotes int4 NOT NULL,
    creation_region varchar(2) NULL,
    app_id int4 NULL,
    scores_last_updated_utc int4 NULL,
    CONSTRAINT submissions_pkey PRIMARY KEY (id),
    CONSTRAINT submissions_app_id_fkey FOREIGN KEY (app_id) REFERENCES public.oauth_apps(id),
    CONSTRAINT submissions_author_id_fkey FOREIGN KEY (author_id) REFERENCES public.users(id),
    CONSTRAINT submissions_board_id_fkey FOREIGN KEY (board_id) REFERENCES public.boards(id),
    CONSTRAINT submissions_domain_ref_fkey FOREIGN KEY (domain_ref) REFERENCES public.domains(id),
    CONSTRAINT submissions_gm_distinguish_fkey FOREIGN KEY (gm_distinguish) REFERENCES public.boards(id),
    CONSTRAINT submissions_is_approved_fkey FOREIGN KEY (is_approved) REFERENCES public.users(id),
    CONSTRAINT submissions_original_board_id_fkey FOREIGN KEY (original_board_id) REFERENCES public.boards(id),
    CONSTRAINT submissions_repost_id_fkey FOREIGN KEY (repost_id) REFERENCES public.submissions(id)
);
CREATE INDEX ix_submissions_author_id ON public.submissions USING btree (author_id);
CREATE INDEX ix_submissions_board_id ON public.submissions USING btree (board_id);
CREATE INDEX submissions_created_utc_desc_idx ON public.submissions USING btree (created_utc DESC);
CREATE INDEX submissions_score_activity_desc_idx ON public.submissions USING btree (score_activity DESC);
CREATE INDEX submissions_score_disputed_desc_idx ON public.submissions USING btree (score_disputed DESC);
CREATE INDEX submissions_score_hot_desc_idx ON public.submissions USING btree (score_hot DESC);
CREATE INDEX submissions_score_top_desc_idx ON public.submissions USING btree (score_top DESC);


-- public.submissions_aux definition

-- Drop table

-- DROP TABLE public.submissions_aux;

CREATE TABLE public.submissions_aux (
    key_id bigserial NOT NULL,
    id int8 NULL,
    title varchar(500) NULL,
    url varchar(2048) NULL,
    body varchar(10000) NULL,
    body_html varchar(20000) NULL,
    ban_reason varchar(128) NULL,
    embed_url varchar(3000) NULL,
    meta_title varchar(512) NULL,
    meta_description varchar(1024) NULL,
    CONSTRAINT submissions_aux_pkey PRIMARY KEY (key_id),
    CONSTRAINT submissions_aux_id_fkey FOREIGN KEY (id) REFERENCES public.submissions(id)
);
CREATE UNIQUE INDEX ix_submissions_aux_id ON public.submissions_aux USING btree (id);
CREATE INDEX submissions_aux_body_trgm_idx ON public.submissions_aux USING gin (body gin_trgm_ops);
CREATE INDEX submissions_aux_title_trgm_idx ON public.submissions_aux USING gin (title gin_trgm_ops);
CREATE INDEX submissions_aux_url_trgm_idx ON public.submissions_aux USING gin (url gin_trgm_ops);


-- public.subscriptions definition

-- Drop table

-- DROP TABLE public.subscriptions;

CREATE TABLE public.subscriptions (
    id bigserial NOT NULL,
    user_id int8 NULL,
    board_id int8 NULL,
    created_utc int8 NULL,
    is_active bool NULL,
    get_notifs bool NULL,
    CONSTRAINT subscriptions_pkey PRIMARY KEY (id),
    CONSTRAINT subscriptions_board_id_fkey FOREIGN KEY (board_id) REFERENCES public.boards(id),
    CONSTRAINT subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE INDEX ix_subscriptions_board_id ON public.subscriptions USING btree (board_id);
CREATE INDEX ix_subscriptions_user_id ON public.subscriptions USING btree (user_id);


-- public.useragents definition

-- Drop table

-- DROP TABLE public.useragents;

CREATE TABLE public.useragents (
    id serial4 NOT NULL,
    kwd varchar(64) NULL,
    reason varchar(256) NULL,
    banned_by int4 NULL,
    mock varchar(256) NULL,
    status_code int4 NULL,
    instaban bool NULL,
    CONSTRAINT useragents_pkey PRIMARY KEY (id),
    CONSTRAINT useragents_banned_by_fkey FOREIGN KEY (banned_by) REFERENCES public.users(id)
);
CREATE INDEX ix_useragents_kwd ON public.useragents USING btree (kwd);


-- public.userblocks definition

-- Drop table

-- DROP TABLE public.userblocks;

CREATE TABLE public.userblocks (
    id serial4 NOT NULL,
    user_id int4 NULL,
    target_id int4 NULL,
    created_utc int4 NULL,
    CONSTRAINT userblocks_pkey PRIMARY KEY (id),
    CONSTRAINT userblocks_target_id_fkey FOREIGN KEY (target_id) REFERENCES public.users(id),
    CONSTRAINT userblocks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE INDEX ix_userblocks_target_id ON public.userblocks USING btree (target_id);
CREATE INDEX ix_userblocks_user_id ON public.userblocks USING btree (user_id);


-- public.votes definition

-- Drop table

-- DROP TABLE public.votes;

CREATE TABLE public.votes (
    id serial4 NOT NULL,
    user_id int4 NULL,
    vote_type int4 NULL,
    submission_id int4 NULL,
    created_utc int4 NULL,
    creation_ip varchar NULL,
    app_id int4 NULL,
    CONSTRAINT votes_pkey PRIMARY KEY (id),
    CONSTRAINT votes_app_id_fkey FOREIGN KEY (app_id) REFERENCES public.oauth_apps(id),
    CONSTRAINT votes_submission_id_fkey FOREIGN KEY (submission_id) REFERENCES public.submissions(id),
    CONSTRAINT votes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE INDEX ix_votes_submission_id ON public.votes USING btree (submission_id);


-- public.bans definition

-- Drop table

-- DROP TABLE public.bans;

CREATE TABLE public.bans (
    id bigserial NOT NULL,
    user_id int4 NULL,
    board_id int4 NULL,
    created_utc int8 NULL,
    banning_mod_id int4 NULL,
    is_active bool NULL,
    mod_note varchar(128) NULL,
    CONSTRAINT bans_pkey PRIMARY KEY (id),
    CONSTRAINT bans_banning_mod_id_fkey FOREIGN KEY (banning_mod_id) REFERENCES public.users(id),
    CONSTRAINT bans_board_id_fkey FOREIGN KEY (board_id) REFERENCES public.boards(id),
    CONSTRAINT bans_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);


-- public.boardblocks definition

-- Drop table

-- DROP TABLE public.boardblocks;

CREATE TABLE public.boardblocks (
    id bigserial NOT NULL,
    user_id int4 NULL,
    board_id int4 NULL,
    created_utc int4 NULL,
    CONSTRAINT boardblocks_pkey PRIMARY KEY (id),
    CONSTRAINT boardblocks_board_id_fkey FOREIGN KEY (board_id) REFERENCES public.boards(id),
    CONSTRAINT boardblocks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);


-- public.client_auths definition

-- Drop table

-- DROP TABLE public.client_auths;

CREATE TABLE public.client_auths (
    id serial4 NOT NULL,
    oauth_client int4 NULL,
    oauth_code varchar(128) NULL,
    user_id int4 NULL,
    scope_identity bool NULL,
    scope_create bool NULL,
    scope_read bool NULL,
    scope_update bool NULL,
    scope_delete bool NULL,
    scope_vote bool NULL,
    scope_guildmaster bool NULL,
    access_token varchar(128) NULL,
    refresh_token varchar(128) NULL,
    access_token_expire_utc int4 NULL,
    CONSTRAINT client_auths_pkey PRIMARY KEY (id),
    CONSTRAINT client_auths_oauth_client_fkey FOREIGN KEY (oauth_client) REFERENCES public.oauth_apps(id),
    CONSTRAINT client_auths_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);


-- public."comments" definition

-- Drop table

-- DROP TABLE public."comments";

CREATE TABLE public."comments" (
    id serial4 NOT NULL,
    author_id int4 NULL,
    parent_submission int4 NULL,
    created_utc int4 NULL,
    edited_utc int4 NULL,
    is_banned bool NULL,
    distinguish_level int4 NULL,
    gm_distinguish int4 NULL,
    deleted_utc int4 NULL,
    purged_utc int4 NULL,
    is_approved int4 NULL,
    approved_utc int4 NULL,
    creation_ip varchar(64) NULL,
    score_disputed float8 NULL,
    score_hot float8 NULL,
    score_top int4 NULL,
    "level" int4 NULL,
    parent_comment_id int4 NULL,
    original_board_id int4 NULL,
    over_18 bool NULL,
    is_offensive bool NULL,
    is_nsfl bool NULL,
    is_bot bool NULL,
    is_pinned bool NULL,
    creation_region varchar(2) NULL,
    app_id int4 NULL,
    upvotes int4 NOT NULL,
    downvotes int4 NOT NULL,
    is_public bool NULL,
    CONSTRAINT comments_pkey PRIMARY KEY (id),
    CONSTRAINT comments_app_id_fkey FOREIGN KEY (app_id) REFERENCES public.oauth_apps(id),
    CONSTRAINT comments_author_id_fkey FOREIGN KEY (author_id) REFERENCES public.users(id),
    CONSTRAINT comments_gm_distinguish_fkey FOREIGN KEY (gm_distinguish) REFERENCES public.boards(id),
    CONSTRAINT comments_original_board_id_fkey FOREIGN KEY (original_board_id) REFERENCES public.boards(id),
    CONSTRAINT comments_parent_comment_id_fkey FOREIGN KEY (parent_comment_id) REFERENCES public."comments"(id),
    CONSTRAINT comments_parent_submission_fkey FOREIGN KEY (parent_submission) REFERENCES public.submissions(id)
);
CREATE INDEX comments_created_utc_desc_idx ON public.comments USING btree (created_utc DESC);
CREATE INDEX comments_score_disputed_desc_idx ON public.comments USING btree (score_disputed DESC);
CREATE INDEX comments_score_hot_desc_idx ON public.comments USING btree (score_hot DESC);
CREATE INDEX comments_score_top_desc_idx ON public.comments USING btree (score_top DESC);
CREATE INDEX ix_comments_author_id ON public.comments USING btree (author_id);
CREATE INDEX ix_comments_original_board_id ON public.comments USING btree (original_board_id);
CREATE INDEX ix_comments_parent_comment_id ON public.comments USING btree (parent_comment_id);
CREATE INDEX ix_comments_parent_submission ON public.comments USING btree (parent_submission);


-- public.comments_aux definition

-- Drop table

-- DROP TABLE public.comments_aux;

CREATE TABLE public.comments_aux (
    key_id serial4 NOT NULL,
    id int4 NULL,
    body varchar(10000) NULL,
    body_html varchar(20000) NULL,
    ban_reason varchar(256) NULL,
    CONSTRAINT comments_aux_pkey PRIMARY KEY (key_id),
    CONSTRAINT comments_aux_id_fkey FOREIGN KEY (id) REFERENCES public."comments"(id)
);
CREATE INDEX comments_aux_body_trgm_idx ON public.comments_aux USING gin (body gin_trgm_ops);
CREATE UNIQUE INDEX ix_comments_aux_id ON public.comments_aux USING btree (id);


-- public.commentvotes definition

-- Drop table

-- DROP TABLE public.commentvotes;

CREATE TABLE public.commentvotes (
    id serial4 NOT NULL,
    user_id int4 NULL,
    vote_type int4 NULL,
    comment_id int4 NULL,
    created_utc int4 NULL,
    creation_ip varchar NULL,
    app_id int4 NULL,
    CONSTRAINT commentvotes_pkey PRIMARY KEY (id),
    CONSTRAINT commentvotes_app_id_fkey FOREIGN KEY (app_id) REFERENCES public.oauth_apps(id),
    CONSTRAINT commentvotes_comment_id_fkey FOREIGN KEY (comment_id) REFERENCES public."comments"(id),
    CONSTRAINT commentvotes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE INDEX ix_commentvotes_comment_id ON public.commentvotes USING btree (comment_id);


-- public.flags definition

-- Drop table

-- DROP TABLE public.flags;

CREATE TABLE public.flags (
    id serial4 NOT NULL,
    post_id int4 NULL,
    user_id int4 NULL,
    created_utc int4 NULL,
    resolution_notif_sent bool NOT NULL,
    CONSTRAINT flags_pkey PRIMARY KEY (id),
    CONSTRAINT flags_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.submissions(id),
    CONSTRAINT flags_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);


-- public.modactions definition

-- Drop table

-- DROP TABLE public.modactions;

CREATE TABLE public.modactions (
    id bigserial NOT NULL,
    user_id int4 NULL,
    board_id int4 NULL,
    kind varchar(32) NULL,
    target_user_id int4 NULL,
    target_submission_id int4 NULL,
    target_comment_id int4 NULL,
    "_note" varchar(256) NULL,
    created_utc int4 NULL,
    CONSTRAINT modactions_pkey PRIMARY KEY (id),
    CONSTRAINT modactions_board_id_fkey FOREIGN KEY (board_id) REFERENCES public.boards(id),
    CONSTRAINT modactions_target_comment_id_fkey FOREIGN KEY (target_comment_id) REFERENCES public."comments"(id),
    CONSTRAINT modactions_target_submission_id_fkey FOREIGN KEY (target_submission_id) REFERENCES public.submissions(id),
    CONSTRAINT modactions_target_user_id_fkey FOREIGN KEY (target_user_id) REFERENCES public.users(id),
    CONSTRAINT modactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE INDEX ix_modactions_board_id ON public.modactions USING btree (board_id);


-- public.notifications definition

-- Drop table

-- DROP TABLE public.notifications;

CREATE TABLE public.notifications (
    id serial4 NOT NULL,
    user_id int4 NULL,
    comment_id int4 NULL,
    submission_id int4 NULL,
    "read" bool NULL,
    CONSTRAINT notifications_pkey PRIMARY KEY (id),
    CONSTRAINT notifications_comment_id_fkey FOREIGN KEY (comment_id) REFERENCES public."comments"(id),
    CONSTRAINT notifications_submission_id_fkey FOREIGN KEY (submission_id) REFERENCES public.submissions(id),
    CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE INDEX ix_notifications_comment_id ON public.notifications USING btree (comment_id);
CREATE INDEX ix_notifications_user_id ON public.notifications USING btree (user_id);


-- public.postrels definition

-- Drop table

-- DROP TABLE public.postrels;

CREATE TABLE public.postrels (
    id bigserial NOT NULL,
    post_id int4 NULL,
    board_id int4 NULL,
    CONSTRAINT postrels_pkey PRIMARY KEY (id),
    CONSTRAINT postrels_board_id_fkey FOREIGN KEY (board_id) REFERENCES public.boards(id),
    CONSTRAINT postrels_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.submissions(id)
);


-- public.reports definition

-- Drop table

-- DROP TABLE public.reports;

CREATE TABLE public.reports (
    id serial4 NOT NULL,
    post_id int4 NULL,
    user_id int4 NULL,
    created_utc int4 NULL,
    board_id int4 NULL,
    CONSTRAINT reports_pkey PRIMARY KEY (id),
    CONSTRAINT reports_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.submissions(id),
    CONSTRAINT reports_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);


-- public.award_relationships definition

-- Drop table

-- DROP TABLE public.award_relationships;

CREATE TABLE public.award_relationships (
    id serial4 NOT NULL,
    user_id int4 NULL,
    submission_id int4 NULL,
    comment_id int4 NULL,
    CONSTRAINT award_relationships_pkey PRIMARY KEY (id),
    CONSTRAINT award_relationships_comment_id_fkey FOREIGN KEY (comment_id) REFERENCES public."comments"(id),
    CONSTRAINT award_relationships_submission_id_fkey FOREIGN KEY (submission_id) REFERENCES public.submissions(id),
    CONSTRAINT award_relationships_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);


-- public.commentflags definition

-- Drop table

-- DROP TABLE public.commentflags;

CREATE TABLE public.commentflags (
    id serial4 NOT NULL,
    user_id int4 NULL,
    comment_id int4 NULL,
    created_utc int4 NULL,
    resolution_notif_sent bool NOT NULL,
    CONSTRAINT commentflags_pkey PRIMARY KEY (id),
    CONSTRAINT commentflags_comment_id_fkey FOREIGN KEY (comment_id) REFERENCES public."comments"(id),
    CONSTRAINT commentflags_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);