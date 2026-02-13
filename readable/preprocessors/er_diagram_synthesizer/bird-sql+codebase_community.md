```mermaid
erDiagram
    Post {
        table posts "Core/current attributes of a post (type, owner, title/body, counts, parent/accepted answer, timestamps)."
        table postHistory "History records of post content/metadata revisions, including editor and timestamps."
    }
    User {
        table users "User profiles (reputation, display name, bio, activity counts, links)."
    }
    Tag {
        table tags "Tag dictionary with tag name, usage count, and references to excerpt/wiki posts."
    }
    Comment {
        table comments "Comments on posts, including text, score, creation time, and optional author."
    }
    Vote {
        table votes "Post votes with type, creation date, optional voter, and bounty information."
    }
    Badge {
        table badges "Badge awards with name, award date, and recipient user."
    }

    %% FROM posts p JOIN users u ON p.OwnerUserId = u.Id
    User }o--o| Post : "UserAuthorsPost"

    %% FROM posts p JOIN users u ON p.LastEditorUserId = u.Id
    User }o--o| Post : "UserLastEditsPost"

    %% FROM postHistory ph JOIN posts p ON ph.PostId = p.Id JOIN users u ON ph.UserId = u.Id
    User }o--o{ Post : "UserRevisesPost"

    %% FROM posts p JOIN comments c ON c.PostId = p.Id
    Post }o--|| Comment : "PostHasComments"

    %% FROM comments c JOIN users u ON c.UserId = u.Id
    User }o--o| Comment : "UserWritesComment"

    %% FROM posts p JOIN votes v ON v.PostId = p.Id
    Post }o--|| Vote : "PostHasVotes"

    %% FROM votes v JOIN users u ON v.UserId = u.Id
    User }o--o| Vote : "UserCastsVote"

    %% FROM users u JOIN badges b ON b.UserId = u.Id
    User }o--|| Badge : "UserAwardedBadge"

    %% FROM postLinks pl JOIN posts p_src ON pl.PostId = p_src.Id JOIN posts p_tgt ON pl.RelatedPostId = p_tgt.Id
    Post }o--o{ Post : "PostRelatedToPost"

    %% FROM posts q JOIN posts a ON q.AcceptedAnswerId = a.Id
    Post |o--o| Post : "PostAcceptsAnswer"

    %% FROM posts q JOIN posts a ON a.ParentId = q.Id
    Post }o--|| Post : "PostHasAnswers"

    %% FROM posts p JOIN tags t ON p.Tags LIKE '%' || '<' || t.TagName || '>' || '%'
    Post }o--o{ Tag : "PostTaggedWithTag"

    %% FROM tags t JOIN posts p ON t.ExcerptPostId = p.Id
    Tag |o--o{ Post : "TagHasExcerptPost"

    %% FROM tags t JOIN posts p ON t.WikiPostId = p.Id
    Tag |o--o{ Post : "TagHasWikiPost"
```