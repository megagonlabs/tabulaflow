```mermaid
erDiagram
    Post {
        table posts "Core post fields including type, body, score, view counts, ownership, parent/accepted-answer self-references, tag text, and edit metadata."
    }
    User {
        table users "Core user profile and reputation/activity metrics."
    }
    Comment {
        table comments "Comment text, score, author (optional), post linkage, and timestamps."
    }
    Vote {
        table votes "Vote type, target post, voter (optional), creation date, and optional bounty amount."
    }
    PostRevision {
        table postHistory "SCD-like history records for posts: revision type, timestamps, editor (optional), text and comments."
    }
    BadgeAward {
        table badges "Award records with badge name, award date, and recipient user."
    }
    Tag {
        table tags "Tag master data including name, usage count, and links to wiki/excerpt posts."
    }

    %% FROM posts p JOIN users u ON u.Id = p.OwnerUserId
    User |o--o{ Post : "UserAuthorsPost"

    %% FROM posts p JOIN users u ON u.Id = p.LastEditorUserId
    User |o--o{ Post : "UserLastEditsPost"

    %% FROM posts q JOIN posts a ON q.AcceptedAnswerId = a.Id
    Post |o--o| Post : "PostHasAcceptedAnswer"

    %% FROM posts answer JOIN posts question ON answer.ParentId = question.Id
    Post }o--o| Post : "PostAnswerOfQuestion"

    %% FROM comments c JOIN users u ON u.Id = c.UserId
    User |o--o{ Comment : "UserAuthorsComment"

    %% FROM comments c JOIN posts p ON p.Id = c.PostId
    Post |o--o{ Comment : "CommentOnPost"

    %% FROM votes v JOIN users u ON u.Id = v.UserId
    User |o--o{ Vote : "UserCastsVote"

    %% FROM votes v JOIN posts p ON p.Id = v.PostId
    Post |o--o{ Vote : "VoteOnPost"

    %% FROM badges b JOIN users u ON u.Id = b.UserId
    User |o--o{ BadgeAward : "UserAwardedBadge"

    %% FROM postHistory h JOIN posts p ON p.Id = h.PostId
    Post |o--o{ PostRevision : "PostHasRevisions"

    %% FROM postHistory h JOIN users u ON u.Id = h.UserId
    User |o--o{ PostRevision : "RevisionAuthoredByUser"

    %% FROM tags t JOIN posts p ON p.Id = t.ExcerptPostId
    Tag |o--o{ Post : "TagHasExcerptPost"

    %% FROM tags t JOIN posts p ON p.Id = t.WikiPostId
    Tag |o--o{ Post : "TagHasWikiPost"

    %% FROM posts p JOIN tags t ON p.Tags LIKE '%<' || t.TagName || '>%'
    Post }o--o{ Tag : "PostTaggedWithTag"

    %% FROM postLinks l JOIN posts source ON source.Id = l.PostId JOIN posts target ON target.Id = l.RelatedPostId
    Post }o--o{ Post : "PostRelatesToPost"
```