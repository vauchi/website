+++
title = "The layer nobody unbundled"
description = """
Everyone wants to break social media into parts you can own. The part
that holds your actual people keeps getting skipped."""
date = 2026-08-21
slug = "the-layer-nobody-unbundled"
+++

There is a
[long-running argument](https://www.aei.org/technology-and-innovation/decentralization-portability-reimagining-social-media-platforms/)
about how to take social media apart.

It goes like this. A platform is not one thing. It is a stack of
separate jobs glued together: who you are, who you know, what gets
posted, what you see first, and who decides when something crosses a
line. Facebook does all of those. It does not have to. Break them
apart, let different people run different parts, and you get to leave
one without losing the rest.

The argument is a good one. Bluesky, Mastodon, and Nostr are all
serious attempts at it. But there is a piece of the stack that keeps
falling out of the diagram, and it is the piece that holds your
actual people.

We are building something for that layer. The cost is worth stating
up front: it only works with people who also use it.

## What gets unbundled, and what does not

Read the serious writing on this and you can watch it happen.

One widely shared
[taxonomy from Tech Policy Press](https://www.techpolicy.press/unbundling-social-media-a-taxonomy-of-problem-areas/)
sorts the whole problem into five areas: speech, business models,
privacy, competition, and whether any of it is technically buildable.
Careful work. It never once discusses your contacts.

A
[Project Liberty interview](https://www.projectliberty.io/news/unbundling-the-social-media-stack-could-a-decentralized-protocol-bring-real-choice-and-control/)
lays out the layers cleanly — the protocol, the apps on top, the
community rules, the money. Wendy Seltzer puts the stakes plainly:
"If we don't have open protocols or access to our own data, it's
harder to take our input elsewhere and rebuild on a new foundation."
She is right. But the data she means is posts and profiles — the
address book never comes up.

The list of connections gets treated as a detail of the identity
problem. It is the one layer whose loss you actually feel. You can
survive a new interface. You can survive a different ranking
algorithm. Losing the ability to reach forty people is a different
kind of injury.

## Portable is not the same as private

Almost every project in this space does the same thing with your
connections. It moves them. Instead of Facebook's database holding
who you know, a shared protocol holds it. Now any app can read your
list, so you can switch apps without starting over. That is real
portability and it solves a real problem.

But look at what portability requires. For a second app to read your
connections, your connections have to be readable. On Bluesky your
follows are
[records in a public repository](https://docs.bsky.app/blog/repo-export)
that anyone can download. On Nostr your contact list is
[published as an ordinary event](https://github.com/nostr-protocol/nips/blob/master/02.md)
that any relay will hand out. Some blockchain-based projects state
the pitch outright: your followers become permanent public entries in
a shared ledger, tied to your account.

This is sold as ownership, and in one sense it is. Nobody can delete
your list. But "who you're connected to" — what researchers call your
social graph — has now gone from *one company's secret* to
*everyone's public record*. For a follower list, that may be a fine
trade. It is a strange trade for the list of people whose home
address and phone number you keep.

Unbundling moved the graph. The harder question — whether it needs to
sit anywhere at all — went unasked.

## The address book was never rented from a protocol

Meanwhile, the layer under all of this went untouched.

Your address book is the oldest social graph you have, and the only
one built entirely out of people you actually met. No algorithm
suggested them. Nobody optimised it. It is a few hundred names that
survived the real filter of you deciding to keep them.

And it is the one you have the least control over. It sits in
Google Contacts or iCloud, syncing quietly. LinkedIn holds the
professional half and shows you ads about it. Every "free" contact
app that asks to import your contacts is asking for the whole graph,
not one name.

Nobody proposed unbundling that. It was already digital, already
working, already boring. So the conversation about owning your
connections skipped straight past the connections that matter most.

## What it looks like to actually remove the middle

Vauchi is our attempt at that missing layer, and the design choice
that follows from all of the above is this: there is no list.

There is no account, no public handle, and no company holding the
record of who you know — not even an encrypted one we promise never
to open. Your contacts live on your phone. When you meet Ana and swap
cards, that happens directly between your two phones. No server is
told and no account is created.

Updates still have to travel. When Ana changes her number, the new
number reaches you through a relay server — a machine in the middle
that passes messages along. It cannot read what changed; only you and
Ana can, because it was encrypted before it left her phone. It also
has no name to attach the message to. Each message is addressed to a
code that changes every day and means nothing by itself. The relay
knows a code received something. It does not know that code is you,
or that Ana sent it.

So the relay never assembles the thing everyone else is busy making
portable. There is no finished list of who knows whom sitting on a
server, waiting to be handed over, subpoenaed, sold in a bankruptcy,
or leaked.

## What this does not do

Three things.

**It only works with people who also use it.** This is the real
cost, and it is not a small one. A protocol that publishes your
follows gets network effects; a design that publishes nothing does
not. Ana has to have the app too. If she doesn't, you are back to
typing a number into your phone like it's 2009.

**The relay is not blind, only ignorant.** It sees that something
was sent, roughly when, and roughly how big it was. We delay each
update by a random moment and round the sizes up to blunt that. A
patient observer watching the whole network may still notice that a
small update left one phone and that a few others fetched something
soon after, and start guessing those phones belong together. We
expect that to be hard, not impossible, and we say so in the same
words in our
[threat model](https://vauchi.app/docs/developers/threat-model.html)
— the published list of what we defend against and what we don't.

There is a less comfortable half to this. Two separate machines are
meant to stand between your phone and the relay, so that neither one
sees both who you are and what you asked for. Today we run both of
them. Nothing technical stops us from putting those two views
together — only our choosing not to, which is exactly the kind of
promise this whole post argues you should not have to accept.
Handing one of those machines to someone else is the plan, and it
has not happened yet.

**None of this un-shares anything.** Once Ana has read your number,
she has it. You can stop sending her updates, quietly and without a
notification. You cannot reach into her screenshots. That is how
sharing works everywhere, and no architecture changes it.

## The null option

The unbundling argument is right that these layers should come apart.
But it assumes every layer, once separated, needs a home somewhere.

Some layers are better with nobody running them. The list of people
you know is the clearest case. It doesn't need a protocol, a chain,
or a company. Updates still have to cross the gap between two phones,
and ours cross a relay. But the list itself belongs on your phone and
on theirs, and should be assembled nowhere in between.

That's not a feature we added. It's the one we left out.
