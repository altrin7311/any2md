---
title: "i was tired of having like 50 tabs open trying to learn ML so i put all the good lectures, papers and blogs in one place (590 docs, free)"
source_url: "https://www.reddit.com/r/learnmachinelearning/comments/1tprnqh/i_was_tired_of_having_like_50_tabs_open_trying_to/"
source_type: reddit
upload_date: 2026-05-28
extraction_date: 2026-05-29
subreddit: "learnmachinelearning"
tags: [machine learning, resources, curated collection]
---

# i was tired of having like 50 tabs open trying to learn ML so i put all the good lectures, papers and blogs in one place (590 docs, free)

> **Summary:** A user shares a collection of machine learning (ML) resources, including lectures, papers, blogs, and YouTube transcripts, in a single repository to facilitate learning.

Key concepts: [[cs229]], [[231n]], [[224n]], [[6.S191]], [[youtube-transcript-api]], [[yt-dlp]]

## Thread

## Comments


**/u/Organic_Scarcity_495**

honestly the hardest part of learning ML for me wasnt the math, it was that all the good stuff is spread everywhere. stanford lectures on youtube, papers as pdfs on arxiv, karpathy on his blog, lilian weng somewhere else, jay alammar's illustrated guides on another site. all different formats, nothing in one place. so i just collected the best of it into one spot: 78 papers (full text) — the classics up to recent stuff like flashattention, mamba, deepseek r1 474 lecture transcripts — stanford (cs229, 231n, 224n etc), MIT 6.S191, andrew ng, karpathy's zero to hero, 3blue1brown, fast.ai, deeplearning.ai, yannic kilcher 38 of the blog posts people always link (jay alammar, lilian weng, sebastian raschka etc) its all just markdown so you can search it, read it in obsidian, throw it in a RAG setup, or fine tune on it. whatever works for you. heres the repo: https://github.com/ATOM00blue/machine-learning-library quick honesty on why this exists: i was actually trying to build a game that teaches ML by playing it. turns out thats really hard to do well lol so i paused it, but all the research i did to prep became this and it felt dumb to let it sit on my drive. might go back to the game later. all credit goes to the people who actually made this stuff, im just the guy who put it in one folder. submitted by /u/Organic_Scarcity_495 [link] [comments]


**/u/eternviking**

Thanks let me bookmark this and forget about it 5 minute later...


**/u/hdreadit**

Godsend. I'm not even going to use this. But I just appreciate your contribution.


**/u/Sure_Functions**

this is GOLD, thanks a lot


**/u/Organic_Scarcity_495**

for anyone curious how i put this together — wrote some python scrapers to pull the youtube transcripts (youtube-transcript-api, with a yt-dlp fallback for when youtube rate-limited me), grabbed the papers off arxiv, and pulled the blogs with readability. then everything gets cleaned and saved as markdown with a little yaml header (title, author, source url, date) so its all consistent and easy to filter/search. the youtube ip-blocking after a couple hundred requests was the most annoying part lol. happy to share more if anyone wants to build something similar.


**/u/Sharp_Level3382**

So you used yt-dlp or youtube-transcripy-a pi ?


**/u/Organic_Scarcity_495**

both — youtube-transcript-api is the main path since its faster and cleaner, and yt-dlp is the fallback for when youtube started ip-blocking me after a couple hundred requests. yt-dlp grabs the auto-caption vtt file and i parse that into text. so api first, yt-dlp as backup.


**/u/Sharp_Level3382**

For me better oposite, using clean curl requests and yt-dlp than youtube-transcript-api that used to block me even by connection through proxy servers


**/u/abs_67**

Dammnn that is soo goodd


**/u/Fit_Fortune953**

great work man, try add even mire resources


**/u/Organic_Scarcity_495**

thanks man! yeah ill keep adding to it over time. its all open source too so if theres anything specific you want added, feel free to open an issue or drop a PR — happy to take contributions


**/u/Realistic-Stress5030**

Thank you so much


**/u/BlueOrchid5334**

Thanks. Im just starting out in ML. I'll take a look at it and see what I can learn.


**/u/Admirable-Mouse2232**

Great work but even you won't read most of it. Forget about others


**/u/Organic_Scarcity_495**

Well I didn't build or gathered this to read in the first place I was trying to build a game using all the info available out there but building a good game is tough not qna or puzzle game, and when it comes to useless of it you can dump that entire corpus into obsidian and connect claude or what ever agent you want for any ml learning or info in Deep


**/u/LeaderAtLeading**

Curating quality ML resources saves time. The real test is whether people actually use a curated collection or just search individually based on what they need right now. Finding where ML learners are asking for help navigating the material matters more than having everything in one place. Leadline.dev surfaces those conversations so you know what people actually struggle with.


**/u/scoshi**

Well, that's less annoying than most ads ... Save a click: Paid service for social marketers (not really related to OPs topic). 3-day free trial.


**/u/pm_me_your_smth**

You just know the platform is complete shit if the dev advertises it everywhere with zero regard for relevancy. I wonder if they realize how dumb this is.


**/u/LeaderAtLeading**

Less annoying than most is the bar we should aim for.


**/u/scoshi**

"Aspire To Mediocrity"

