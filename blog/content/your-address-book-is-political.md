+++
title = "Your address book is political"
description = """
Big Tech did not just take our attention. It took the way we find each
other. Why we are building a contact card that only works when two
people meet."""
date = 2026-10-14
slug = "your-address-book-is-political"
+++

In the late 1960s, women meeting in small discussion groups started
saying something that sounds obvious once it is said out loud: *the
personal is political.* Problems each of them had been told were hers
alone — the housework, the body, the marriage — turned out to be
shared, and shaped by the same forces. Carol Hanisch, whose
[1969 essay](https://www.carolhanisch.org/CHwritings/PIP.html) made the
phrase famous, put it plainly: "There are no personal solutions at this
time. There is only collective action for a collective solution."

A new book borrows that slogan and gives it a twist. In
[*Resisting Big Tech: The Personalized is Political*](https://doi.org/10.5040/9781350504134),
free to read online, the cultural scholar Niels Niessen argues that
the feeds, matches, suggestions and reminders that feel made just for
you are not a private matter either. They are built by a handful of
companies, out of the same raw material, for the same reason.

We read it as people building a contact app. It put into words
something we had been circling for a long time.

## Life as a stream

Niessen's central image is the *stream*. Everyday life used to be the
part nobody had organized: the time after work, drifting from one
thing to the next, the friend you happen to bump into. Now most of it
runs through an account. Watching a film, finding a date, keeping up
with friends, getting directions — each happens inside somebody's
app, logged in.

That can feel like *more* privacy. Your own feed, your own settings,
your own private chats. In 2019 Mark Zuckerberg
[told a conference](https://www.nbcnews.com/tech/tech-news/facebook-redesign-privacy-push-highlight-zuckerberg-s-efforts-leave-troubles-n1000216)
"I believe that the future is private," and WhatsApp messages really
are encrypted. But private, Niessen points out, can mean two things:
personal to you, and owned by them. Your conversations became the
second kind.

What is being taken, he argues, is not only your time or your
attention. Quoting the writer McKenzie Wark, he names it: "our
sociability, our common and ordinary life together." The raw material
is the way people find, reach and keep each other.

## Locking the letters is not enough

This is where it lands for us.

Most talk about privacy is about *what you say*. Can anyone read my
messages? Encryption answered that, and it was a real victory. But
the words were never the most valuable part. A former Facebook ads
manager
[explained in Wired](https://www.wired.com/story/facebooks-listening-smartphone-microphone/)
why the company does not need to secretly listen through your
microphone: it already "can find you on whatever device" you have ever
used it on. It knows who you are, who you talk to, when, and how
often.

The map of who knows whom is worth more than anything said along it.
And that map has a homely name: your address book.

Every messaging app starts by asking to read it. Every "find your
friends" button uploads it. Google or Apple keeps a copy. LinkedIn
holds the work half and sells ads around it. The people you actually
know — not followers, not matches, the people whose number you chose
to keep — are the one part of your social life you have never really
held yourself.

## A contact card that only works when you meet

Vauchi is our attempt to hand that back. Here is how, and how it
lines up with the book.

**You swap cards in person.** One phone shows a square code, the
other scans it, in the same room. There is no account, no username,
and no search box where a stranger can type your name. Niessen asks
for places where people meet as part of ordinary life, not because an
algorithm matched them. We cannot build a café. We can refuse to
build a directory, so the only way into your address book stays the
old one: you met.

**It is slow on purpose.** The tech industry praises anything
"frictionless." Niessen argues the opposite: the small frictions —
the detour, the chance meeting, the effort — are where life actually
happens. Having to stand next to someone to add them is slower than
tapping "follow." That is the point.

**You choose what each person sees.** Your work number to one person,
your home address to another. Anything new you add to your card
starts hidden from everyone. Niessen spends a chapter on consent and
quotes a short film about it: "look for a yes, because anything less
than that is a no." The film was made by Tinder, and he does not let
the irony pass — a company preaching consent while collecting data on
terms few people read. We took the line and left the company: nobody
sees a detail of yours until you say so, one person at a time.

**Nobody holds the list.** Your contacts live on your phone. When a
friend changes their number, the update travels to you through a
server we run, like a sealed letter through a post office. It cannot
open the letter, and the address on it is a code that changes every
day, so it does not know who it is for. There is no complete map of
who knows whom on our server, because we never built a server that
could hold one.

**It does not want your attention.** No feed, no streaks, no
notifications designed to pull you back, and nothing that tells a
contact whether you looked at their card. Niessen describes the
smartphone as a machine that calls out to us all day long. A contact
card should not be one more voice in that crowd.

**Nobody profits from your data.** No ads, no tracking, no investors
waiting for a return. The code is public and free for anyone to read
and reuse. We do not say that out of purity. It is the only way we
know to keep the address book from quietly becoming a product again.

## The part an app cannot do

Niessen is wary of anyone who thinks the answer to Big Tech is a
better app, and he is right. Resisting on your own, he writes, "is
almost a contradiction in terms." Switching apps by yourself does not
change the world you live in.

Vauchi agrees with him in one stubborn way: you cannot use it alone. A
card is useless until someone else has one too, and the only way to
share it is to meet. As we wrote in
[an earlier post](https://vauchi.app/blog/the-layer-nobody-unbundled/),
that is our biggest cost. It is also the closest a piece of software
gets to what the book asks for: something people do together, not
something one person consumes.

The book ends with three tasks. Talk about these platforms honestly,
as businesses that profit from how people connect. Build
not-for-profit alternatives. And slow everyday life down enough to
make room for each other again. We are working on the second. The
first and the third are not ours to build. They happen between
people, in conversations and in rooms, as people decide together what
they will and will not hand over.

## What we are not claiming

The book is honest about its limits, so we should be too.

**It still runs on a smartphone.** Niessen ends with cobalt, mined in
Congo under brutal conditions, inside every phone. A privacy app does
not change what the phone is made of.

**It will not get you off the big platforms.** Your friends are on
WhatsApp, your school uses Google, your job uses Teams. Vauchi
replaces none of that. It takes one thing — the list of who you know
and how to reach them — out of their hands.

**You still have to trust us a little.** Our server cannot read your
updates, and the codes on them do not say who you are. But it can see
that something was sent, roughly when, and roughly how big. And today
we also run the machine that sits between your phone and that server,
so for now you are trusting us not to compare notes. Our
[threat model](https://vauchi.app/docs/developers/threat-model.html)
lists what we protect against and what we do not.

**It is early.** Vauchi is not finished. It is not yet ready to be the
only place your contacts live.

## Why we are building it anyway

Niessen does not offer optimism, and neither will we. He borrows a
distinction from the critic Terry Eagleton: optimism is a story about
how things will turn out; hope acts because the act is worth doing,
whatever happens next.

An address book is a small thing. But it is the oldest social network
any of us has, and the only one made entirely of people we chose to
keep. It should belong to the people in it. That is why we are
building Vauchi.
