# Calm Before Breakfast

Static signup page for the Calm Before Breakfast daily email. Hosted on GitHub Pages at calmbeforebreakfast.com.

## Local preview

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000

## Before going live

The signup form already posts to Kit form `10168577`:

```
https://app.kit.com/forms/10168577/subscriptions
```

In the Kit form settings, set the success redirect to:

```
https://calmbeforebreakfast.com/thank-you.html
```

The `CNAME` file is already set to `calmbeforebreakfast.com`. After this repo is on GitHub, enable GitHub Pages and point DNS at it.

## Files

- `index.html` and `style.css`: the signup page
- `thank-you.html`: shown after a successful signup
- `CNAME`: GitHub Pages custom domain
- `favicon.svg`

Copy and colors come from the approved landing draft. Do not use em dashes or en dashes, and do not add health or medical claims.
