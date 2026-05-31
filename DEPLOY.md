# Deploying Rob's Coffee (Netlify Drop)

This is the easiest way to get a public shareable URL.

## One-time Deploy (Netlify Drop)

1. Open this link in your browser:
   https://app.netlify.com/drop

2. In your file manager, navigate to this folder:
   ~/projects/robs-coffee/

3. Drag the file `index.html` onto the Netlify Drop page.

4. Wait 5–10 seconds.

5. You will get a public URL like:
   https://random-name-123abc.netlify.app

You can now share this URL with anyone.

## How to Update the Site Later

1. Run the updater:
   ```bash
   python3 update_coffee.py
   ```

2. Copy the updated file over index.html:
   ```bash
   cp robs-coffee.html index.html
   ```

3. Go back to https://app.netlify.com/drop

4. Drag the new `index.html` onto the page again.

Netlify will update your existing site with the new version.

## Tips

- The site is completely static and free.
- No login required for basic Drop usage.
- If you want a nicer URL later, you can connect the site to a free Netlify account and claim a custom subdomain.
- You can also switch to GitHub Pages later for better version control.

Enjoy sharing Rob's Coffee! ☕
