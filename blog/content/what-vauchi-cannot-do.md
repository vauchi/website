+++
title = "What Vauchi can't do"
description = """
The reasonable things people hope a private contact app does, that this
one does not — written down before you need to find out."""
date = 2026-11-11
slug = "what-vauchi-cannot-do"
+++

Privacy tools tend to describe what they protect and leave you to
discover the edges yourself, usually at the worst possible moment.

So here are the edges. Every limit below is already in our
[threat model](https://vauchi.app/docs/developers/threat-model.html) — the
document that lists which risks Vauchi defends against and which remain —
sitting in the same table as the guarantees. This is the plain-language
version.

## It only helps with people who also use it

Start here, because it is the limit that decides whether any of the rest
matters to you.

Vauchi keeps your details current for people who installed it and swapped
cards with you. Not for your dentist, your bank, or the four hundred
people holding a business card you handed out in 2019. If you change your
number, the people who get it automatically are the ones who opted in
too. Everyone else still needs the group text.

That is a smaller promise than "never send a new-number message again",
and it is the true one.

## It cannot take back what you already shared

You decide, per person, which of your details they can see. You can
change that whenever you like, withdraw it, or stop someone receiving any
further update. Vauchi sends them no notification that you did, though
they may still notice that your card stopped changing.

What none of that does is reach into someone's head.

If a person has read your phone number, they have your phone number.
They may have written it down, screenshotted the card, or copied it into
another address book weeks ago. We can stop the flow of new information;
we cannot retrieve what already arrived — and neither can any app that
tells you it can.

## It is not anonymity

Vauchi's purpose is to give real contact details to real people you
actually met. Your number, your email, sometimes your address. It is not
an alias service, not a throwaway number, and it does not hide your real
details behind a forwarding service.

What it removes is the account and the platform in the middle. There is
no username to register and no company holding the list of who you know.

That distinction matters, because "private" gets used for both and they
are not the same. Vauchi aims at privacy *from the infrastructure* — with
the relay limits described below — not privacy *from your contacts*.
Your contacts are supposed to be able to reach you. That is the feature.

## It cannot make an unequal relationship equal

Every exchange is mutual. You both walk away holding a card, and
neither of you can quietly take without giving.

What each of you gives is a separate decision. So the exchange is
even in shape and can be lopsided in content. A new manager can take
your mobile number and hand back a work email. Vauchi will not stop
that, and it will not tell you it happened — you see the card they
chose to send, not the one they could have.

We thought about forcing the two sides to match, and decided against
it. Plenty of exchanges are properly lopsided: you give a tradesperson
your address, they give you a phone number, and nobody has been
wronged. A rule that made those equal would break more than it fixed.

So the app does not flatten status. It hands you the same lever
the other person has, and leaves the two of you to it.

## It is not protection from someone dangerous

This is the limit we most want people to read.

Vauchi can stop sending someone updates without telling them, and for
some situations that property genuinely matters. It is still not safety.

It cannot make you unfindable. It cannot undo what someone already
knows. It does nothing about a person with physical access to you or
your phone, which is how a great deal of real harm actually happens.

If you are dealing with an abusive or stalking situation, please build
your plan with people who do this work rather than with an app. In the
United States, the National Domestic Violence Hotline (thehotline.org)
and NNEDV's Safety Net project (techsafety.org) both publish guidance on
technology and abuse; elsewhere, a local domestic violence service will
know the equivalent. Any tool, including this one, is at most a small
part of a plan built with someone who understands your situation.

## The relay sees the envelope, not the letter

When your details change, the update reaches your contacts through a
relay server. Your phone cannot hold an open line to everyone you know —
that would drain the battery — so updates wait at the relay until the
phone next checks in.

The relay cannot read your details: they are end-to-end encrypted, which
here means only you and the contact you swapped with hold the keys — not
the relay, not us. Updates are addressed by codes that change daily, so
the relay is never handed a lasting list of who knows whom.

It does see that something arrived, roughly when, and roughly how big it
was. That is metadata — information about an update rather than its
contents, the envelope rather than the letter — and no design removes it
entirely. Timing is deliberately blurred. Updates are also padded with
extra bytes, so they look more alike in size. Even so, our threat model
is careful here: a patient observer watching over a long period may
still infer connections from the pattern. How much the blurring helps is a
design expectation, not something we have measured.

One more thing we would rather you heard from us. The design splits the
work between two relays: one sees the address of your internet
connection, the other sees the request for updates, so no single server
sees both. Today Vauchi runs both of those
hops. Independent operation is the target and the design assumes it, but
until that happens the separation is a matter of our conduct rather than
something the structure enforces on us. You can also run your own relay,
though we recognise that is a real answer for very few people.

## Updates are not instant

When a friend changes their number, you will not see it the same second.

Part of the wait is on purpose. The first relay holds each request for
a random stretch of up to fifteen minutes before passing it on. That
makes the timing of your phone checking in harder to match with what it
asked for. That blurring is one of the protections described above — it makes
matching harder but does not prevent it — and it costs you minutes.

Most of the rest is your phone. To save battery, iPhones and Android
phones decide when an app may run in the background, and a phone left
locked on a desk overnight may let it run only every few hours. On
Android, Vauchi also ties its saved data to your screen lock, so it
cannot read it while the phone stays locked. So today, a phone that
stays locked usually picks up changes after you unlock it, often within
roughly a quarter of an hour, and longer if either phone has a poor
connection.

Picture it: your sister changes her number at nine in the evening and
your phone is face down on the kitchen table until morning. You will
most likely see her new number some minutes after you pick it up, not at
nine.

For a contact card that is usually fine. For "I'm outside, which door?"
it is not, and that is what messages and calls are for.

## It is not stronger than your device

Your keys live in your platform's secure store — the iOS Keychain or
Android KeyStore — rather than loose on disk. That helps against a lost
phone. It does not help against a phone that is unlocked and in someone
else's hands, or one that has been thoroughly compromised.

Encryption protects data while it travels and while it sits at rest. It
has never protected a screen someone is already looking at.

## It asks you to make decisions

Most contact apps ask you one question: may this app see your address
book? Say yes, and it sees every detail of everyone in it, and the
absence of further questions feels like ease. Vauchi asks who sees
what, and that is work you did not previously have to do.

We have tried hard to keep the bill small. A new detail starts hidden.
After that you share it with everyone you swapped cards with, with a
group, or with people you pick. If you want a work card and a personal
card, groups do that, and you set the details once for the group rather
than for each member. Groups are optional, and the app suggests common
ones rather than asking you to invent a filing system.

Still, it is a model you have to hold in your head. If you build
groups, you maintain them. A friendship that changed two years ago
does not update your settings for you, and nothing in the app will
nag you about it. An app that nags you about permissions has just
moved the work rather than removed it.

If what you want is a contact app that never asks you anything, this
is not it, and we would rather you knew that now than after the
third settings screen.

## It is not finished

The apps are not released. Everything on our site describes what is being
built and tested, not something you can install this afternoon, and the
sign-up form is a waitlist rather than a download.

We would rather say that plainly than let a polished website imply
otherwise.

## Why write this down

Partly because a guarantee published without its limits isn't much of a
guarantee.

Mostly for a more practical reason. The people most likely to want
something like Vauchi are the ones most likely to be hurt by believing a
promise that was never true. A limit you learn on the website costs you
nothing; the same limit learned later can cost a great deal.

The longer version lives at
[what Vauchi is not](https://vauchi.app/docs/about/what-vauchi-is-not.html),
and the design it comes from is in the
[threat model](https://vauchi.app/docs/developers/threat-model.html).

If any of it ever stops matching how Vauchi works, that is our mistake
to correct, here and in the app.
