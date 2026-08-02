+++
title = "Your contact details were never meant to be permanent"
description = """
A number, an inbox, a profile. We treat them as who we are. They were
only ever meant to say where we happen to be."""
date = 2026-08-02
slug = "never-meant-to-be-permanent"
+++

Think about what a phone number actually is. It is a routing
instruction. It says: to reach this person, send the signal here. It
was never meant to say anything about who you are, any more than a seat
number says something about the passenger.

Somewhere along the way that flipped. Your number became your identity.
Your work email became your professional identity. Your profile on a
platform became the version of you that other people can find. We
started treating the address as the person.

And addresses, unlike people, are supposed to change.

## The quiet cost of a permanent address

Ana changes her mobile number. Nothing dramatic — she moved country,
and the old plan made no sense.

What follows is not one problem. It is fifty small ones, spread over a
year. The dentist has the old number. Her aunt has the old number. The
person she met at a conference and genuinely meant to work with has the
old number, and will simply conclude she was not interested. The
group text goes out, half the people miss it, and for months she keeps
discovering someone else who quietly fell off the edge.

Now notice the strange part. Ana did nothing wrong. She changed a
routing instruction. The cost she paid was the cost of every
relationship that had been indexed by that instruction.

So most people do the rational thing: they don't change it. They keep
the number they hate, the inbox that leaks, the account on the platform
they stopped enjoying years ago — because leaving is priced in
relationships, and nobody wants to pay in those.

That is a switching cost. Whether every instance of it was designed or
merely never fixed, the effect on Ana is the same.

## What actually changed recently

It would be easy, and a bit lazy, to blame this on artificial
intelligence.

Contact details have been leaking for two decades. Data brokers have
bought and resold them for longer than that. Breaches spill them by the
million. None of that is new, and none of it needs AI.

What is changing is how cheaply the scattered pieces can be put back
together — connecting a number to a name, to an old address, to an
employer. We are not going to pretend to have measured that, and you
should be suspicious of anyone who quotes you a figure for it. But the
direction is not seriously in doubt, and the direction is the part that
matters: if old information about you gets easier to reassemble every
year, then being able to *move* — to change how you are reached without
losing everyone — stops being an inconvenience.

We think it starts to look like something you ought to be able to
expect. That is a value judgement, and we would rather label it as one
than smuggle it in as a technical fact.

## Who is collecting this

"Data brokers" sounds abstract, so here is something you can check
rather than take from us. California makes them register, and publishes
[the register](https://cppa.ca.gov/data_brokers/): companies whose
business is holding details about people they have never met, listed by
name. The state also runs a
[deletion portal](https://privacy.ca.gov/drop-for-data-brokers) that
brokers must start honouring in August 2026.

The same rules require brokers to declare whether they have shared what
they hold with law enforcement, foreign actors, or — in the regulator's
own words — "developers of generative AI systems". That question only
gets written into law once the answer matters.

Vauchi fixes none of that. We cannot remove you from a broker's
database, and anyone who claims they can is worth doubting. What we can
do is not add to the pile: no account, no profile, and nothing legible
on our side to sell.

## The reframe

Here is a different way to think about the ordinary act of swapping
contact details with someone.

Right now, when you give someone your number, you are giving them a
copy of a fact. Facts go stale. Copies drift. Neither of you can fix
it later without doing the work again.

What if you were giving them something else — not the fact, but a
connection to you, which knows how to answer the question "how do I
reach this person?" *at the time it is asked* rather than at the time
it was written down?

That is a small change, and it is what Vauchi is: a contact card you
swap with someone — in person, or by a one-off link when you can't be
in the same room — which stays current afterwards. No account, and no
company holding the list of who you know. Change your number once, and
the people you swapped with have the new one.

## The honest shape of that

Three things, and they matter more than anything above.

**It only works with people who also use it.** This is the big one, and
it is the question every article like this dodges. Vauchi keeps your
details current for people who installed it and swapped cards with you.
Ana's dentist is not going to do that. Her aunt might. The colleague she
actually wanted to keep might. Nobody should read the story above and
think a new app would have saved all fifty relationships — it would have
saved the ones where both people opted in, which is a smaller and more
honest promise.

**It does not un-share what you already shared.** If you gave someone
your number, they have it. You can stop sending them updates, quietly
and at any time, and you can decide per person which details they see at
all. What you cannot do is reach into their memory, their screenshots,
or the copy they pasted somewhere else. Neither can we. Any product that
implies otherwise is selling you something.

**It is not anonymity.** Vauchi shares real details — number, email,
sometimes an address — with people you deliberately chose. That is the
point of it. What it removes is the account and the platform in the
middle. There is still a relay server that passes updates along, and we
have written down exactly what it can and cannot observe rather than
rounding it to "nothing".

There is also a fourth thing, which is simply that Vauchi is not
finished. It is being built in the open, and the apps are not out yet.
The site has a waitlist, not a download.

## The point

Your relationships are not the same kind of thing as your phone number.
One is worth keeping. The other is a routing instruction that should be
free to change.

The whole design follows from refusing to confuse the two.

*The full list of what Vauchi defends against — and the limitations
sitting in the same table as the guarantees — is published at
[vauchi.app/docs](https://vauchi.app/docs). The source is public too.
That is not much use to most readers on its own, which is why the
limitations are written in plain words rather than left for people who
can read Rust.*
