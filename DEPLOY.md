# Deploy

The briefing is a static GitHub Pages site:

https://robbittsaunders.github.io/coffee/

A scheduled GitHub Action refreshes the data three times a day. To refresh and publish by hand:

```bash
python3 update_coffee.py
npm run deploy
```

`npm run deploy` copies `robs-coffee.html` to `index.html`, commits, and pushes. The existing Pages workflow then publishes it.
