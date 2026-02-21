```sql
-- Database: GITHUB_REPOS_DATE

/*
Schema: YEAR
Table: "_{YEAR}" (YEAR from 2011 to 2023)
Rows: 149590
Sample rows:
| type        | public   | payload                                                                                                                                                                                                     | repo   | actor   | org   | created_at       | id         | other   |
|-------------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|---------|-------|------------------|------------|---------|
| GistEvent   | True     | {"name":"gist: 831984","desc":"Performance Is Not A Level, It’s A Logger [blog] [log4net]","actor":"...imer = Stopwatch.StartNew();","actor_gravatar":"d4df53ad45289d052ae918287d869082","action":"create"} | {
  "name": "/",
  "url": "https://api.github.dev/repos//"
}        | {
  "avatar_url": "https://secure.gravatar.com/avatar/d4df53ad45289d052ae918287d869082?d=http://gith...id": 217842,
  "login": "AnthonyMastrean",
  "url": "https://api.github.dev/users/AnthonyMastrean"
}         | null  | 1297958508000000 | 1137327268 | [NULL]  |
| FollowEvent | True     | {"target":{"type":"User","public_repos":3,"avatar_url":"https://secure.gravatar.com/avatar/c5b8ce272...html_url":"https://github.com/luzem","following":1,"id":723969,"created_at":"2011-04-12T04:04:03Z"}} | {
  "name": "/",
  "url": "https://api.github.dev/repos//"
}        | {
  "avatar_url": "https://secure.gravatar.com/avatar/a4a2351ad883f4b439895fe8f5c968b2?d=http://gith...f5c968b2",
  "id": 291754,
  "login": "tblobaum",
  "url": "https://api.github.dev/users/tblobaum"
}         | null  | 1321156692000000 | 1498362423 | [NULL]  |
| FollowEvent | True     | {"target":{"gravatar_id":"f1a051208dad513a5a57695bac3df13a","repos":5,"followers":24,"login":"spiceee"},"actor":"leonardorb","actor_gravatar":"ea23c3ceaf98e205cb76c616bfad8574"}                           | {
  "name": "/",
  "url": "https://api.github.dev/repos//"
}        | {
  "avatar_url": "https://secure.gravatar.com/avatar/ea23c3ceaf98e205cb76c616bfad8574?d=http://gith...d8574",
  "id": 37300,
  "login": "leonardorb",
  "url": "https://api.github.dev/users/leonardorb"
}         | null  | 1302316251000000 | 1241175457 | [NULL]  |
| GistEvent   | True     | {"action":"update","gist":{"created_at":"2011-10-20T19:38:34Z","comments":0,"public":true,"files":{}...tem.  This can speed up IO-intensive operations (e.g. loading a large and heavily indexed table.)"}} | {
  "name": "/",
  "url": "https://api.github.com/repos//"
}        | {
  "avatar_url": "https://secure.gravatar.com/avatar/43ff41a4e194d6603e2ccd6eb20d0ca5?d=%2Fimages%2...0d0ca5",
  "id": 435652,
  "login": "jaytaylor",
  "url": "https://api.github.com/users/jaytaylor"
}         | null  | 1319154146000000 | 1493780179 | [NULL]  |
| FollowEvent | True     | {"target":{"blog":"www.zachwill.com","name":null,"type":"User","avatar_url":"https://secure.gravatar...ithub.com/zachwill","hireable":true,"following":24,"id":172692,"created_at":"2009-12-27T20:25:16Z"}} | {
  "name": "/",
  "url": "https://api.github.dev/repos//"
}        | {
  "avatar_url": "https://secure.gravatar.com/avatar/e9f49dbb385e52ac4b570e00fb56f4d5?d=http://gith...f4d5",
  "id": 183869,
  "login": "chorfa672m",
  "url": "https://api.github.dev/users/chorfa672m"
}         | null  | 1320791365000000 | 1497466629 | [NULL]  |
| ...         | ...      | ...                                                                                                                                                                                                         | ...    | ...     | ...   | ...              | ...        | ...     |
*/
CREATE TABLE YEAR."_{YEAR}" (
    "type" VARCHAR NOT NULL,
        -- <values>{'CommitCommentEvent', 'CreateEvent', 'DeleteEvent', 'DownloadEvent', 'Event', 'FollowEvent', 'ForkApplyEvent', 'ForkEvent', 'GistEvent', 'GollumEvent', 'IssueCommentEvent', 'IssuesEvent', 'MemberEvent', 'PublicEvent', 'PullRequestEvent', 'PushEvent', 'WatchEvent'}</values>
    "public" BOOLEAN NOT NULL,
        -- <example>True</example>
    "payload" VARCHAR NOT NULL,
        -- <example>'{"number":40,"pull_request":{"number":40,"issue_ur...puppetlabs"}},"state":"closed"},"action":"closed"}'</example>
    "repo" VARIANT NOT NULL,
        -- <example>'{
  "id": 1366684,
  "name": "residuen/OpenEdu-XYP...api.github.dev/repos/residuen/OpenEdu-XYPlotter"
}'</example>
    "actor" VARIANT NOT NULL,
        -- <example>'{
  "avatar_url": "https://secure.gravatar.com/ava...: "https://api.github.dev/users/AnthonyMastrean"
}'</example>
    "org" VARIANT NOT NULL,
        -- <example>'null'</example>
    "created_at" DECIMAL NOT NULL,
        -- <example>1297958508000000</example>
    "id" VARCHAR NOT NULL,
        -- <example>'1497879839'</example>
    "other" VARCHAR NULL
);

/*
Schema: MONTH
Table: "_{YYYYMM}" (YYYYMM from 201102 to 202410)
Rows: 179734
Sample rows:
| type        | public   | payload                                                                                                                                                                                                     | repo   | actor   | org   | created_at       | id         | other   |
|-------------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|---------|-------|------------------|------------|---------|
| PushEvent   | True     | {"shas":[["f6b62ca9db6f4578bbb501f30a3ddd505169e5c8","be5e7e7e33948ec2a45c2f5ab660d62519087d69@destr...578bbb501f30a3ddd505169e5c8","actor_gravatar":"0ee02e2b40c05f894de4a3cf85e76bed","push_id":24719669} | {
  "name": "/",
  "url": "https://api.github.dev/repos//"
}        | {
  "avatar_url": "https://secure.gravatar.com/avatar/?d=http://github.dev%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
  "url": "https://api.github.dev/users/"
}         | null  | 1297649706000000 | 1130463801 | [NULL]  |
| CreateEvent | True     | {"name":"add-a-testimonial---Facebook-profile-picture-user-recommending","object":"repository","object_name":null}                                                                                          | {
  "name": "/",
  "url": "https://api.github.dev/repos//"
}        | {
  "avatar_url": "https://secure.gravatar.com/avatar/?d=http://github.dev%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
  "url": "https://api.github.dev/users/"
}         | null  | 1297576006000000 | 1129327217 | [NULL]  |
| CreateEvent | True     | {"name":"android_dalvik","object":"repository","object_name":null}                                                                                                                                          | {
  "name": "/",
  "url": "https://api.github.dev/repos//"
}        | {
  "avatar_url": "https://secure.gravatar.com/avatar/?d=http://github.dev%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
  "url": "https://api.github.dev/users/"
}         | null  | 1298416882000000 | 1147498877 | [NULL]  |
| IssuesEvent | True     | {"number":131,"repo":"testUserBesol/Test4","actor":"testUserBesol","issue":632963,"actor_gravatar":"3f1dc467cb9c28074d63d388963ee358","action":"closed"}                                                    | {
  "name": "/",
  "url": "https://api.github.dev/repos//"
}        | {
  "avatar_url": "https://secure.gravatar.com/avatar/?d=http://github.dev%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
  "url": "https://api.github.dev/users/"
}         | null  | 1298850990000000 | 1156374467 | [NULL]  |
| IssuesEvent | True     | {"number":31,"repo":"testUserBesol/Test4","actor":"testUserBesol","issue":632400,"actor_gravatar":"3f1dc467cb9c28074d63d388963ee358","action":"closed"}                                                     | {
  "name": "/",
  "url": "https://api.github.dev/repos//"
}        | {
  "avatar_url": "https://secure.gravatar.com/avatar/?d=http://github.dev%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
  "url": "https://api.github.dev/users/"
}         | null  | 1298836910000000 | 1155942544 | [NULL]  |
| ...         | ...      | ...                                                                                                                                                                                                         | ...    | ...     | ...   | ...              | ...        | ...     |
*/
CREATE TABLE MONTH."_{YYYYMM}" (
    "type" VARCHAR NOT NULL,
        -- <values>{'CommitCommentEvent', 'CreateEvent', 'DeleteEvent', 'DownloadEvent', 'FollowEvent', 'ForkApplyEvent', 'ForkEvent', 'GistEvent', 'GollumEvent', 'IssuesEvent', 'MemberEvent', 'PublicEvent', 'PullRequestEvent', 'PushEvent', 'WatchEvent'}</values>
    "public" BOOLEAN NOT NULL,
        -- <example>True</example>
    "payload" VARCHAR NOT NULL,
        -- <example>'{"shas":[["e25010a71098e77ff4c35da443027781408263c...a5efa94588ff009f9f67c7d41ba7d","push_id":25118994}'</example>
    "repo" VARIANT NOT NULL,
        -- <example>'{
  "id": 943826,
  "name": "sirfilip/FavoriteFile...s://api.github.dev/repos/sirfilip/FavoriteFiles"
}'</example>
    "actor" VARIANT NOT NULL,
        -- <example>'{
  "avatar_url": "https://secure.gravatar.com/ava...  "url": "https://api.github.dev/users/sirfilip"
}'</example>
    "org" VARIANT NOT NULL,
        -- <example>'null'</example>
    "created_at" DECIMAL NOT NULL,
        -- <example>1297649706000000</example>
    "id" VARCHAR NOT NULL,
        -- <example>'1140145149'</example>
    "other" VARCHAR NULL
);

/*
Schema: DAY
Table: "_{YYYYMMDD}" (YYYYMMDD from 20110212 to 20241022 except 20111231, 20121231, 20131231, 20141231, 20151231, 20200822, 20210508, 20210510, 20210511, 20210826, 20211026, 20211027, 20211028)
Rows: 32197
Sample rows:
| type        | public   | payload                                                                                                                                                                                                     | repo   | actor   | org    | created_at       | id         | other   |
|-------------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|---------|--------|------------------|------------|---------|
| WatchEvent  | True     | {"repo":"jamierumbelow/pipesphp.org","actor":"ws0x9","actor_gravatar":"3905c7c81c9f34d37ff3504ecd667168","action":"started"}                                                                                | {
  "id": 1352415,
  "name": "jamierumbelow/pipesphp.org",
  "url": "https://api.github.dev/repos/jamierumbelow/pipesphp.org"
}        | {
  "avatar_url": "https://secure.gravatar.com/avatar/?d=http://github.dev%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
  "url": "https://api.github.dev/users/"
}         | [NULL] | 1297530753000000 | 1128353130 | [NULL]  |
| ForkEvent   | True     | {"repo":"melarrosa/VB-Cash-Register","actor":"hbisa","forkee":1358011,"actor_gravatar":"e52ebe7e17fbaae6a6379d7a1b49323a"}                                                                                  | {
  "id": 1345423,
  "name": "melarrosa/VB-Cash-Register",
  "url": "https://api.github.dev/repos/melarrosa/VB-Cash-Register"
}        | {
  "avatar_url": "https://secure.gravatar.com/avatar/?d=http://github.dev%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
  "url": "https://api.github.dev/users/"
}         | [NULL] | 1297496501000000 | 1127648760 | [NULL]  |
| ForkEvent   | True     | {"repo":"edavis10/redmine","actor":"MerchantsBonding","forkee":1359058,"actor_gravatar":"79bb849cc8a2650a44279c2087937f7a"}                                                                                 | {
  "id": 21692,
  "name": "edavis10/redmine",
  "url": "https://api.github.dev/repos/edavis10/redmine"
}        | {
  "avatar_url": "https://secure.gravatar.com/avatar/?d=http://github.dev%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
  "url": "https://api.github.dev/users/"
}         | [NULL] | 1297528399000000 | 1128231329 | [NULL]  |
| IssuesEvent | True     | {"number":46,"repo":"snoyberg/yesod","actor":"hpfarr","actor_gravatar":"e8f9e986f643a2e9be7646f8b3f58c16","issue":593253,"action":"opened"}                                                                 | {
  "id": 237904,
  "name": "snoyberg/yesod",
  "url": "https://api.github.dev/repos/snoyberg/yesod"
}        | {
  "avatar_url": "https://secure.gravatar.com/avatar/?d=http://github.dev%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
  "url": "https://api.github.dev/users/"
}         | [NULL] | 1297472596000000 | 1127289146 | [NULL]  |
| PushEvent   | True     | {"shas":[["23e579b141261105d4b5765f0249fe64bfb28bc4","a9df78b4b5c00745f26b0821b2cc57336a474862@cloud...105d4b5765f0249fe64bfb28bc4","actor_gravatar":"459b9ff2f2f1773e9ec15d4b6ef60e14","push_id":24669423} | {
  "id": 1352664,
  "name": "daniel-cloudspace/feature-girl",
  "url": "https://api.github.dev/repos/daniel-cloudspace/feature-girl"
}        | {
  "avatar_url": "https://secure.gravatar.com/avatar/?d=http://github.dev%2Fimages%2Fgravatars%2Fgravatar-user-420.png",
  "url": "https://api.github.dev/users/"
}         | [NULL] | 1297536772000000 | 1128526502 | [NULL]  |
| ...         | ...      | ...                                                                                                                                                                                                         | ...    | ...     | ...    | ...              | ...        | ...     |
*/
CREATE TABLE DAY."_{YYYYMMDD}" (
    "type" VARCHAR NOT NULL,
        -- <values>{'CommitCommentEvent', 'CreateEvent', 'DeleteEvent', 'DownloadEvent', 'FollowEvent', 'ForkApplyEvent', 'ForkEvent', 'GistEvent', 'GollumEvent', 'IssuesEvent', 'MemberEvent', 'PublicEvent', 'PullRequestEvent', 'PushEvent', 'WatchEvent'}</values>
    "public" BOOLEAN NOT NULL,
        -- <example>True</example>
    "payload" VARCHAR NOT NULL,
        -- <example>'{"shas":[["c7c2ff4f6f1fc99e91e320533d9375d7ba23365...0db865e7de86f337499bd20cb2740","push_id":24667457}'</example>
    "repo" VARIANT NOT NULL,
        -- <example>'{
  "id": 1352415,
  "name": "jamierumbelow/pipesp...api.github.dev/repos/jamierumbelow/pipesphp.org"
}'</example>
    "actor" VARIANT NOT NULL,
        -- <example>'{
  "avatar_url": "https://secure.gravatar.com/ava...0.png",
  "url": "https://api.github.dev/users/"
}'</example>
    "org" VARIANT NULL,
        -- <example>'{
  "avatar_url": "https://secure.gravatar.com/ava...  "url": "https://api.github.dev/orgs/bioclipse"
}'</example>
    "created_at" DECIMAL NOT NULL,
        -- <example>1297530753000000</example>
    "id" VARCHAR NOT NULL,
        -- <example>'1127648760'</example>
    "other" VARCHAR NULL
);

/*
Schema: GITHUB_REPOS
Table: languages
Rows: 3325634
Sample rows:
| repo_name                    | language   |
|------------------------------|------------|
| bmancini55/buzzrd-admin      | []         |
| MBAOS/A                      | []         |
| nahron/anwia                 | []         |
| kevinmarx/node-bean          | []         |
| aman-kumayu/wikipedia_viewer | []         |
| ...                          | ...        |
*/
CREATE TABLE GITHUB_REPOS.languages (
    "repo_name" VARCHAR NOT NULL,
        -- <example>'willem66745/dailyschedule-rust'</example>
    "language" VARIANT NOT NULL
        -- <example>'[]'</example>
);

/*
Schema: GITHUB_REPOS
Table: licenses
Rows: 3325634
Sample rows:
| repo_name                     | license   |
|-------------------------------|-----------|
| keyarmory/keyarmory-php       | isc       |
| tangrams/geojson-vt-cpp       | isc       |
| Lughino/node-translate-server | isc       |
| xNekOIx/swift-sodium          | isc       |
| MJKWoolnough/form             | isc       |
| ...                           | ...       |
*/
CREATE TABLE GITHUB_REPOS.licenses (
    "repo_name" VARCHAR NOT NULL,
        -- <example>'magiclud/LogowanieFacebook'</example>
    "license" VARCHAR NOT NULL
        -- <values>{'agpl-3.0', 'apache-2.0', 'artistic-2.0', 'bsd-2-clause', 'bsd-3-clause', 'cc0-1.0', 'epl-1.0', 'gpl-2.0', 'gpl-3.0', 'isc', 'lgpl-2.1', 'lgpl-3.0', 'mit', 'mpl-2.0', 'unlicense'}</values>
);

/*
Schema: GITHUB_REPOS
Table: sample_commits
Rows: 17976
Sample rows:
| commit                                   | tree                                     | parent   | author   | committer   | subject                                                                                                                                                                                                     | message   | trailer   | difference   | difference_truncated   | repo_name      | encoding   |
|------------------------------------------|------------------------------------------|----------|----------|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|-----------|--------------|------------------------|----------------|------------|
| 01ffe339e3a0ba5ecbeb2b3b5abac7b3ef90f374 | 7586fb091466772a31d9e46d807b8709d4166ef8 | [
  "4a8e4a270b89030bdeb09d2f8cef7cfe9a50e54d"
]          | {
  "date": 1137448927000000,
  "email": "e2e3f1f24cbc439f8c1ba9b08f9954237d64be64@bruce",
  "name": "Nathan Scott",
  "time_sec": 1137448927,
  "tz_offset": 660
}          | {
  "date": 1137448927000000,
  "email": "e2e3f1f24cbc439f8c1ba9b08f9954237d64be64@bruce",
  "name": "Nathan Scott",
  "time_sec": 1137448927,
  "tz_offset": 660
}             | Make alloc_page_buffers() initialise buffer_heads using init_buffer(), like other routines here, to ... initialised with respect to b_private/b_end_io.  Fixes an odd interaction between XFS and reiserfs. | Make alloc_page_buffers() initialise buffer_heads using init_buffer(),
like other routines here, to ...n
XFS and reiserfs.

Signed-off-by: Nathan Scott <e2e3f1f24cbc439f8c1ba9b08f9954237d64be64@sgi.com>           | [
  {
    "email": "e2e3f1f24cbc439f8c1ba9b08f9954237d64be64@sgi.com",
    "key": "Signed-off-by",
    "value": "Nathan Scott <e2e3f1f24cbc439f8c1ba9b08f9954237d64be64@sgi.com>"
  }
]           | [
  {
    "new_mode": 33188,
    "new_path": "fs/buffer.c",
    "new_sha1": "3dc712f29d2d60fe4bdac9d...188,
    "old_path": "fs/buffer.c",
    "old_sha1": "7cdf48a9a50105c4a074d53f807077c398f4fdb5"
  }
]              | [NULL]                 | torvalds/linux | [NULL]     |
| 9fd8e5a25ecb0febfad321c04478a9d8b8b247f7 | 84f1c7453bcbb93e05d9f0ca30e63580547a7754 | [
  "84eb186bc37c0900b53077ca21cf6dd15823a232"
]          | {
  "date": 1416132204000000,
  "email": "3efd2a027b14fd890cd23a9ef6d1134b4e5ad850@skynet.be",
  "name": "Fabian Frederick",
  "time_sec": 1416132204,
  "tz_offset": 60
}          | {
  "date": 1421499606000000,
  "email": "014f16385c5a8ff1646b588a3d5169b595c0f10e@gmx.de",
  "name": "Peter Huewe",
  "time_sec": 1421499606,
  "tz_offset": 60
}             | tpm: remove unnecessary sizeof(u8)                                                                                                                                                                          | tpm: remove unnecessary sizeof(u8)

sizeof(u8) is always 1.

Signed-off-by: Fabian Frederick <3efd2a...34b4e5ad850@skynet.be>
Signed-off-by: Peter Huewe <014f16385c5a8ff1646b588a3d5169b595c0f10e@gmx.de>           | [
  {
    "email": "3efd2a027b14fd890cd23a9ef6d1134b4e5ad850@skynet.be",
    "key": "Signed-off-by",... "Signed-off-by",
    "value": "Peter Huewe <014f16385c5a8ff1646b588a3d5169b595c0f10e@gmx.de>"
  }
]           | [
  {
    "new_mode": 33188,
    "new_path": "drivers/char/tpm/tpm_i2c_stm_st33.c",
    "new_sha1": ...ivers/char/tpm/tpm_i2c_stm_st33.c",
    "old_sha1": "4669e3713428509d7f96c69ba5a31714bbae7f38"
  }
]              | [NULL]                 | torvalds/linux | [NULL]     |
| 7a1d7e6dd76a2070e2d86826391468edc33bb6d6 | 11faf31b48a14e1b6d07c0494458ccd5d1f79994 | [
  "313d21eeab9282e01fdcecd40e9ca87e0953627f"
]          | {
  "date": 1418413598000000,
  "email": "6e0a3da6445cd298bc4a6b3aaa269075849c9510@linux.intel.com",
  "name": "Jarkko Sakkinen",
  "time_sec": 1418413598,
  "tz_offset": -480
}          | {
  "date": 1421499611000000,
  "email": "014f16385c5a8ff1646b588a3d5169b595c0f10e@gmx.de",
  "name": "Peter Huewe",
  "time_sec": 1421499611,
  "tz_offset": 60
}             | tpm: TPM 2.0 baseline support                                                                                                                                                                               | tpm: TPM 2.0 baseline support

TPM 2.0 devices are separated by adding a field 'flags' to struct
tpm... copy paste error * 2]
Signed-off-by: Peter Huewe <014f16385c5a8ff1646b588a3d5169b595c0f10e@gmx.de>           | [
  {
    "email": "014f16385c5a8ff1646b588a3d5169b595c0f10e@gmx.de",
    "key": "Signed-off-by",
    "value": "Peter Huewe <014f16385c5a8ff1646b588a3d5169b595c0f10e@gmx.de>"
  }
]           | [
  {
    "new_mode": 33188,
    "new_path": "drivers/char/tpm/Makefile",
    "new_sha1": "88848edb0...a1": "1abe6502219f258f15e69de50aa3a2434247f116",
    "old_path": "drivers/char/tpm/tpm2-cmd.c"
  }
]              | [NULL]                 | torvalds/linux | [NULL]     |
| 313d21eeab9282e01fdcecd40e9ca87e0953627f | c33c8a7d1bc2c589a7673e3781c4d3538059c896 | [
  "71ed848fd791bc0b53a1b7a04f29eb9e994c7cbb"
]          | {
  "date": 1418413597000000,
  "email": "6e0a3da6445cd298bc4a6b3aaa269075849c9510@linux.intel.com",
  "name": "Jarkko Sakkinen",
  "time_sec": 1418413597,
  "tz_offset": -480
}          | {
  "date": 1421499610000000,
  "email": "014f16385c5a8ff1646b588a3d5169b595c0f10e@gmx.de",
  "name": "Peter Huewe",
  "time_sec": 1421499610,
  "tz_offset": 60
}             | tpm: device class for tpm                                                                                                                                                                                   | tpm: device class for tpm

Added own device class for TPM. Uses MISC_MAJOR:TPM_MINOR for the
first c...5169b595c0f10e@gmx.de>
Signed-off-by: Peter Huewe <014f16385c5a8ff1646b588a3d5169b595c0f10e@gmx.de>           | [
  {
    "email": "6e0a3da6445cd298bc4a6b3aaa269075849c9510@linux.intel.com",
    "key": "Signed-of... "Signed-off-by",
    "value": "Peter Huewe <014f16385c5a8ff1646b588a3d5169b595c0f10e@gmx.de>"
  }
]           | [
  {
    "new_mode": 33188,
    "new_path": "Documentation/ABI/stable/sysfs-class-tpm",
    "new_sh...ath": "drivers/char/tpm/tpm_tis.c",
    "old_sha1": "9e02489a94f3b6f6d9824c7d54bc7acb169e3f5c"
  }
]              | [NULL]                 | torvalds/linux | [NULL]     |
| 60ecd86c4d985750efa0ea3d8610972b09951715 | e77cc93d980046a77258d13944ac191d38dec6eb | [
  "eb6301160dde0227ac27c6ec2a0b57054d88e398"
]          | {
  "date": 1444263111000000,
  "email": "586dce2b5b41882e50b9a0eefaf3387b8b8c8cc6@linux.vnet.ibm.com",
  "name": "Hon Ching \\(Vicky\\) Lo",
  "time_sec": 1444263111,
  "tz_offset": -240
}          | {
  "date": 1445209249000000,
  "email": "014f16385c5a8ff1646b588a3d5169b595c0f10e@gmx.de",
  "name": "Peter Huewe",
  "time_sec": 1445209249,
  "tz_offset": 120
}             | vTPM: fix memory allocation flag for rtce buffer at kernel boot                                                                                                                                             | vTPM: fix memory allocation flag for rtce buffer at kernel boot

At ibm vtpm initialzation, tpm_ibmv...c6@linux.vnet.ibm.com>
Signed-off-by: Peter Huewe <014f16385c5a8ff1646b588a3d5169b595c0f10e@gmx.de>           | [
  {
    "email": "4fbacc2fa0ffdbb11bf1ad6925b886ebd08dd15f@kernel.org",
    "key": "Cc",
    "valu... "Signed-off-by",
    "value": "Peter Huewe <014f16385c5a8ff1646b588a3d5169b595c0f10e@gmx.de>"
  }
]           | [
  {
    "new_mode": 33188,
    "new_path": "drivers/char/tpm/tpm_ibmvtpm.c",
    "new_sha1": "3e6a...: "drivers/char/tpm/tpm_ibmvtpm.c",
    "old_sha1": "27ebf9511cb41cdf5e26fc1f82a65ecab9a60d33"
  }
]              | [NULL]                 | torvalds/linux | [NULL]     |
| ...                                      | ...                                      | ...      | ...      | ...         | ...                                                                                                                                                                                                         | ...       | ...       | ...          | ...                    | ...            | ...        |
*/
CREATE TABLE GITHUB_REPOS.sample_commits (
    "commit" VARCHAR NOT NULL,
        -- <example>'44a30220bc0a171c010e8df63d144655abdafe61'</example>
    "tree" VARCHAR NOT NULL,
        -- <example>'60221a5006aaec5e0a810facb8a223b910f92175'</example>
    "parent" VARIANT NOT NULL,
        -- <example>'[
  "4a8e4a270b89030bdeb09d2f8cef7cfe9a50e54d"
]'</example>
    "author" VARIANT NOT NULL,
        -- <example>'{
  "date": 1355788909000000,
  "email": "85dcca6e...",
  "time_sec": 1355788909,
  "tz_offset": -480
}'</example>
    "committer" VARIANT NOT NULL,
        -- <example>'{
  "date": 1355793319000000,
  "email": "69652cac...",
  "time_sec": 1355793319,
  "tz_offset": -480
}'</example>
    "subject" VARCHAR NOT NULL,
        -- <example>'drivers/rtc/rtc-tegra.c: use struct dev_pm_ops for power management'</example>
    "message" VARCHAR NOT NULL,
        -- <example>'Omnikey Cardman 4000: pull in ioctl.h in user head...b940640ad396ab71f93cacec34f@linux-foundation.org>
'</example>
    "trailer" VARIANT NOT NULL,
        -- <example>'[
  {
    "email": "85dcca6eaef7f88f8513274f73363a...0ad396ab71f93cacec34f@linux-foundation.org>"
  }
]'</example>
    "difference" VARIANT NOT NULL,
        -- <example>'[
  {
    "new_mode": 33261,
    "new_path": "scri...: "cd251d5f3f1a4fbde8a0858a9ed5483c60936d01"
  }
]'</example>
    "difference_truncated" BOOLEAN NULL,
    "repo_name" VARCHAR NOT NULL,
        -- <values>{'Microsoft/vscode', 'apple/swift', 'facebook/react', 'tensorflow/tensorflow', 'torvalds/linux', 'twbs/bootstrap'}</values>
    "encoding" VARCHAR NULL
        -- <values>{'ISO-8859-1', 'ISO-8859-2'}</values>
);

/*
Schema: GITHUB_REPOS
Table: sample_contents
Rows: 24286
Sample rows:
| id                                       | size   | content   | binary   | copies   | sample_repo_name                 | sample_ref        | sample_path                                   | sample_mode   | sample_symlink_target   |
|------------------------------------------|--------|-----------|----------|----------|----------------------------------|-------------------|-----------------------------------------------|---------------|-------------------------|
| 2dd586a19b594a73e9c6f7485d1e5da9203a4467 | 21447  | /*
 * rtc-ds1305.c -- driver for DS1305 and DS1306 SPI RTC chips
 *
 * Copyright (C) 2008 David Brow...N("RTC driver for DS1305 and DS1306 chips");
MODULE_LICENSE("GPL");
MODULE_ALIAS("spi:rtc-ds1305");           | False    | 256      | wandboard-org/linux              | refs/heads/master | drivers/rtc/rtc-ds1305.c                      | 33188         | [NULL]                  |
| 7acfd43a7914620c9fef2196f9cac65d0f542d53 | 41645  | /**
 * Core.js 0.9.11
 * https://github.com/zloirock/core-js
 * License: http://rock.mit-license.org...define&&define.amd?define(function(){return b}):c.core=b}();
//# sourceMappingURL=library.min.js.map           | False    | 256      | jsdelivr/jsdelivr                | refs/heads/master | files/core-js/0.9.12/library.min.js           | 33188         | [NULL]                  |
| 9eb0c3299f21b4d86029ebbbf0b6ad8c0945b35d | 3144   | <?php
/*
V5.19  23-Apr-2014  (c) 2000-2014 John Lim (jlim#natsoft.com). All rights reserved.
  Relea...n ('SYSCAT','SYSIBM','SYSSTAT') order by 1,2");
		return rs2html($rs,false,false,false,false);
	}
}           | False    | 256      | happyman/twmap                   | refs/heads/master | twmap_gen/lib/adodb5/perf/perf-db2.inc.php    | 33188         | [NULL]                  |
| 816b2d7412b432d86a4a36147255ec664f760193 | 3974   | /*
 *  linux/drivers/devfreq/governor_simpleondemand.c
 *
 *  Copyright (C) 2011 Samsung Electronics...d\n", __func__, ret);

	return;
}
module_exit(devfreq_simple_ondemand_exit);
MODULE_LICENSE("GPL");           | False    | 1        | garwedgess/android_kernel_lge_g4 | refs/heads/M      | drivers/devfreq/governor_simpleondemand.c     | 33188         | [NULL]                  |
| ca151cab87aa4ba9286dd5b3557fd75bb902c442 | 3025   | @import url("default.css");

body {
    background-color: white;
    margin-left: 1em;
    margin-ri...095C4;
}

.refcount {
    color: #060;
}

.stableabi {
    color: #229;
}
p.logo {
    margin: 0;
}           | False    | 1        | nigelsmall/py2neo                | refs/heads/v3     | book/_themes/pydoctheme/static/pydoctheme.css | 33188         | [NULL]                  |
| ...                                      | ...    | ...       | ...      | ...      | ...                              | ...               | ...                                           | ...           | ...                     |
*/
CREATE TABLE GITHUB_REPOS.sample_contents (
    "id" VARCHAR NOT NULL,
        -- <example>'7af009950c1286d9434b6fa8f2efba9bfd6d1088'</example>
    "size" DECIMAL NOT NULL,
        -- <example>21447</example>
    "content" VARCHAR NULL,
        -- <example>'/**
 *  JQuery Idle.
 *  A dead simple jQuery plug...e.call()):d||(d=!0,l.onShow.call())})})}}(jQuery);'</example>
    "binary" BOOLEAN NOT NULL,
        -- <example>True</example>
    "copies" DECIMAL NOT NULL,
        -- <example>256</example>
    "sample_repo_name" VARCHAR NOT NULL,
        -- <example>'Hlkz/Acore'</example>
    "sample_ref" VARCHAR NOT NULL,
        -- <example>'refs/heads/lammps-icms'</example>
    "sample_path" VARCHAR NOT NULL,
        -- <example>'plugins/subversion/svn-cat-command.c'</example>
    "sample_mode" DECIMAL NOT NULL,
        -- <example>33188</example>
    "sample_symlink_target" VARCHAR NULL
        -- <values>{'dark_system-help.svg', 'gpm-keyboard-000.svg', 'unicode/1f6b0.png'}</values>
);

/*
Schema: GITHUB_REPOS
Table: sample_files
Rows: 524077
Sample rows:
| repo_name   | ref               | path                                                                     | mode   | id                                       | symlink_target                                      |
|-------------|-------------------|--------------------------------------------------------------------------|--------|------------------------------------------|-----------------------------------------------------|
| np/ling     | refs/heads/master | fixtures/strict-par-success/fun1_to_proc_par2.ll                         | 40960  | 316ad972693d0355c3504729fff14287419e004d | ../all/fun1_to_proc_par2.ll                         |
| np/ling     | refs/heads/master | tests/failure/wrong_order_par_seq_middle.t/wrong_order_par_seq_middle.ll | 40960  | daa40d563068ee94f01b1e87952d607a6588a589 | ../../../fixtures/all/wrong_order_par_seq_middle.ll |
| np/ling     | refs/heads/master | fixtures/strict-par-success/layout_case.ll                               | 40960  | 6bd679ec4ff94d8149986d49b8e789d1b4d6a44a | ../all/layout_case.ll                               |
| np/ling     | refs/heads/master | fixtures/strict-par-success/merger_loli_Sort.ll                          | 40960  | 0cfcfb70b14958a8ba30cb83808c9bcc25516969 | ../all/merger_loli_Sort.ll                          |
| np/ling     | refs/heads/master | fixtures/failure/infer_recv.ll                                           | 40960  | de516c994d6cc8b7bcc1fb6bf986699fced404f6 | ../all/infer_recv.ll                                |
| ...         | ...               | ...                                                                      | ...    | ...                                      | ...                                                 |
*/
CREATE TABLE GITHUB_REPOS.sample_files (
    "repo_name" VARCHAR NOT NULL,
        -- <example>'erikd/haskell-big-integer-experiment'</example>
    "ref" VARCHAR NOT NULL,
        -- <example>'refs/heads/dev'</example>
    "path" VARCHAR NOT NULL,
        -- <example>'arch/powerpc/kernel/ptrace.c'</example>
    "mode" DECIMAL NOT NULL,
        -- <example>40960</example>
    "id" VARCHAR NOT NULL,
        -- <example>'c811289b61e21628f28d79b71f27651c39e3e024'</example>
    "symlink_target" VARCHAR NULL
        -- <example>'../all/my_loli.ll'</example>
);

/*
Schema: GITHUB_REPOS
Table: sample_repos
Rows: 400000
Sample rows:
| repo_name                                 | watch_count   |
|-------------------------------------------|---------------|
| kbandla/APTnotes                          | 256           |
| bigcompany/hook.io                        | 256           |
| H07000223/FlycoDialog_Master              | 256           |
| veficos/reverse-engineering-for-beginners | 256           |
| oblac/jodd                                | 256           |
| ...                                       | ...           |
*/
CREATE TABLE GITHUB_REPOS.sample_repos (
    "repo_name" VARCHAR NOT NULL,
        -- <example>'gephi/gephi'</example>
    "watch_count" DECIMAL NOT NULL
        -- <example>256</example>
);
```