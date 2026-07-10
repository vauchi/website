+++
title = "Interoperability without permission"
description = """
The EU declined to force social networks to interoperate. What that
means for the social graph — and why the contact layer can be opened
without any gatekeeper's permission."""
date = 2026-07-10
slug = "eu-interoperability-contact-layer"
+++

You don't stay on a social network because its feed is good. You stay
because the people are there — and leaving means losing them. In
April 2026, the European Commission decided to keep it that way: it
declined to extend the Digital Markets Act's interoperability mandate
to social networking. Messaging gatekeepers still have to open up;
social networks do not, and there is no timeline for revisiting the
question. The Commission's reasoning, set out in its [first DMA
review report](https://digital-markets-act.ec.europa.eu/system/files/2026-04/DMA%20Review%20Report_COM_2026_178_1_EN.pdf),
was that there is little clear demand from users and businesses, and
that the technical complexity is too high. The [EFF called it what it
is](https://www.eff.org/deeplinks/2026/07/european-commission-chooses-keep-eu-users-locked-behind-big-techs-gates):
a decision to keep EU users locked behind Big Tech's gates.

We build a contact app, not a social network, so you might expect this
decision not to concern us. It concerns us directly — because the thing
the gates actually lock in is not content. It's your relationships.

## What the gates hold

Platform lock-in decomposes into two assets:

1. **The social graph** — who you are connected to.
2. **The content layer** — what flows over those connections, and who
   decides what you see.

Nearly the entire European regulatory debate is about the second layer.
The [DSA can audit recommender
systems](https://dsa-observatory.eu/2026/02/15/reclaiming-the-algorithm-what-the-dsa-can-and-cant-fix-about-recommender-systems/),
ban manipulative design, and demand transparency, but researchers
studying it conclude that the structural problem — engagement
optimization under the private control of a handful of companies —
survives all of it. The most credible structural remedy on the table,
letting users [swap in independent recommender
systems](https://dsa-observatory.eu/2026/02/23/reclaiming-the-algorithm-part2/),
explicitly depends on access to the first layer: the social graph. No
graph access, no meaningful alternative.

And that is exactly the access the Commission just declined to mandate.

The graph is the moat — the reason leaving costs you people. Every
"European alternative" and every federated network runs into the same
wall: your network doesn't move with you.

## Interoperability without permission

Here is the thing about your address book: it predates every platform,
and it will outlive every platform. It is the one piece of social
infrastructure that has never belonged to a gatekeeper — paper
address books and phone directories, then SIM cards and phone
contacts, then cloud accounts. The platforms' great trick of the last
twenty years was convincing everyone to rebuild it inside their
walls, where it could be held hostage.

Vauchi is built on a simple inversion: the social graph belongs at
the contact layer, held by the people in it, not by any platform —
including us. The mechanics are deliberately simple: two people meet,
scan each other's QR codes, and each keeps a copy of the other's
contact card. That in-person exchange is the security anchor — you
verified the person by recognizing them, not by trusting a platform.
When meeting isn't possible, two people can exchange through a shared
link instead — and the card's trust level, derived purely from how
the exchange happened and editable by no one, honestly records the
weaker verification.
From then on, the card is a direct, end-to-end encrypted channel
between the two of you. It carries whatever its owner chooses to
share: phone numbers, email, and — crucially — where to find them on
any platform.

That last part is where the interoperability shows up:

- When someone moves — new messenger, new social network, new email,
  new country — they update their card once. Say Ana leaves WhatsApp
  for Signal: she edits one field, and everyone holding her card sees
  the new handle the next time their app syncs. The update travels
  end-to-end encrypted through a relay that only ever sees
  ciphertext — and that routes by anonymous, daily-rotating tokens,
  so it cannot map who knows whom either (the
  [threat model](https://docs.vauchi.app/developers/threat-model.html)
  is public). WhatsApp is never involved, or even aware.

- Migration stops being a network event. Leaving a platform no longer
  means losing people; it means editing one field. The switching cost
  the Commission decided not to dismantle by mandate quietly deflates
  when the graph lives underneath the platforms instead of inside them.

- No gatekeeper API is required. This kind of interoperability cannot
  be lobbied away, delayed for "technical complexity," or declined for
  lack of "clear demand" — because it never needed permission in the
  first place.

There is a happier corollary. The same cards that make leaving cheap
make arriving less lonely: as friends add their Signal or Mastodon
handles, you can see — on your own device, visible to nobody else —
which of your people are already there. The hardest part of joining a
better platform was never installing it; it is the fear that nobody
you know is on the other side. A contact layer answers that before
you jump, one friend at a time — no campaign, no coordinated exodus,
just individual choices becoming quietly visible to the people who
already know each other. Lock-in works by hiding your options. A
graph you hold yourself shows them — which may do more for the
Signals and Mastodons of the world than any mandate would have.

## What this doesn't fix

We are not going to oversell this.

A contact layer only connects people who both use it. A regulation
binds gatekeepers whether or not anyone switched yet; our approach
helps you exactly as far as it spreads, one deliberate exchange at a
time. That is slower. It is also the only route left standing. And
there is intentionally no discovery layer: Vauchi connects people who
already know each other; it doesn't find you an audience.

It does nothing about feeds. Vauchi has no timeline, no recommender,
no engagement metrics — by design, it is a tool you open when you need
it, not a destination. If you care about fixing algorithmic curation
(you should — the [evidence connecting engagement optimization to
polarization](https://www.iese.edu/insight/articles/polarization-social-media-democracy/)
keeps piling up), that fight is at the content layer, and it still
needs regulators, researchers, and better platforms.

And knowing where someone went is not the same as wanting to follow
them there. A portable graph lowers the cost of keeping people when
platforms churn; it doesn't decide where the conversation happens.

## The era this is built for

The platform landscape is fragmenting: X exoduses, Bluesky, Mastodon,
and now [EU-endorsed European
platforms](https://www.techpolicy.press/europes-w-social-bet-tests-its-vision-of-digital-sovereignty/).
Some of these will thrive; most will not; all of them ask you to
rebuild your network inside their walls, one more time.

Every fragmentation makes a platform-neutral contact layer more
valuable, because it is the only layer where all of those worlds can
meet. The Commission has decided the gates stay closed for now. Fine.
The more durable answer was never to ask the gatekeepers to open them —
it is to hold your relationships somewhere no gate can enclose:
with the people themselves.

That's what we're building — and *building* is the operative word:
Vauchi is in active development, not yet released. If you want it
when it ships, [join the waitlist](https://vauchi.app/#waitlist).
