# Next PMS — Day-to-Day Operations

## Build & Deploy

### Local Development
```bash
# Start Frappe backend
cd /Users/sayanthns/frappe-bench && bench start

# Start Vue dev server (HMR, port 8081)
cd apps/next_pms/frontend && yarn dev

# Build for production (local testing at localhost:8000)
cd apps/next_pms/frontend && yarn build
```
**Note:** The Vite dev server at `localhost:8081` can't authenticate with Frappe. All API calls return 403. Always test via the production build at `localhost:8000` after `yarn build`.

### Production Deployment
```bash
# SSH into server
sshpass -p 'enfono123' ssh -o StrictHostKeyChecking=no root@156.67.105.6

# Switch to app user
su - v15
cd frappe-bench

# CRITICAL: Set correct site first
bench use office

# Pull latest code
cd apps/next_pms && git pull origin main

# Run database migrations (if doctype changes)
cd ../.. && bench migrate

# Build Vue frontend
cd apps/next_pms/frontend && yarn build

# Restart all services
sudo supervisorctl restart all
```

### Quick Deploy (no migration needed)
For Python-only or frontend-only changes where no doctype schema changed:
```bash
sshpass -p 'enfono123' ssh root@156.67.105.6 \
  "su - v15 -c 'cd frappe-bench/apps/next_pms && git pull origin main && cd frontend && yarn build' && sudo supervisorctl restart all"
```

### Deploy from Local Machine (automated)
```bash
# Git pull + restart (Python changes only, no build needed)
sshpass -p 'enfono123' ssh root@156.67.105.6 \
  "su - v15 -c 'cd frappe-bench/apps/next_pms && git pull origin main' && sudo supervisorctl restart all"

# Full deploy (migration + build + restart)
sshpass -p 'enfono123' ssh root@156.67.105.6 \
  "su - v15 -c 'cd frappe-bench && bench use office && cd apps/next_pms && git pull origin main && cd ../.. && bench migrate && cd apps/next_pms/frontend && yarn build' && sudo supervisorctl restart all"
```

## Rollback a Bad Deploy

### Option 1: Git revert (safe)
```bash
# On server as v15 user
cd frappe-bench/apps/next_pms
git log --oneline -5         # Find the last good commit
git revert HEAD              # Revert last commit
cd frontend && yarn build
sudo supervisorctl restart all
```

### Option 2: Git reset (destructive, use only if revert fails)
```bash
cd frappe-bench/apps/next_pms
git reset --hard <good-commit-hash>
cd frontend && yarn build
sudo supervisorctl restart all
# If doctype schema changed, also: bench --site office migrate
```

### Option 3: Database rollback (for migration issues)
```bash
# Restore from backup
bench --site office restore /path/to/backup.sql.gz
bench migrate
```

## Accessing Logs

### Frappe/Gunicorn Logs
```bash
# On server as v15 user
tail -f frappe-bench/logs/web.error.log     # Python errors
tail -f frappe-bench/logs/web.log           # Request logs
tail -f frappe-bench/logs/worker.error.log  # Background job errors
tail -f frappe-bench/logs/scheduler.log     # Scheduler task output
```

### Frappe Error Log (in-app)
```
https://office.enfono.com/app/error-log
```
Shows all Python tracebacks. Filter by "next_pms" to find portal-related errors.

### Browser Console (frontend)
Open DevTools → Console. Look for:
- `Failed to load...` — API errors (usually 403 permission issues)
- `Failed to fetch notifications` — Common benign error if notifications API isn't whitelisted
- Network tab → filter by `api/method/next_pms` to see all PMS API calls and responses

### Supervisor Process Status
```bash
sudo supervisorctl status
# Shows: frappe-bench-web, frappe-bench-workers, frappe-bench-redis, frappe-bench-node-socketio
```

## Debugging Issues

### Test an API on server
```bash
# As v15 user
cd frappe-bench
bench --site office console
```
Then in the console:
```python
frappe.set_user("Administrator")
from next_pms.api.portal import get_customer_users
result = get_customer_users()
print(result)
exit()
```

### Test API via curl
```bash
# Login first
curl -s -c cookies.txt -X POST "http://localhost:8000/api/method/login" -d "usr=Administrator&pwd=admin"

# Then call any API
curl -s -b cookies.txt -X POST "http://localhost:8000/api/method/next_pms.api.portal.get_all_support_tickets" | python3 -m json.tool
```

### Check database directly
```bash
bench --site office mariadb
```
Then SQL queries. Table names are backtick-escaped: `` `tabPMS Task` ``, `` `tabPMS Sprint` ``, etc.

## Common Workflows

### Grant Portal Access to a Customer
1. Ensure user exists in Frappe with `PMS Customer` role (User Management tab)
2. Go to Settings → Client Portal tab → click "Grant Access"
3. Select customer user and project
4. System auto-enables `client_portal_enabled` on the project
5. Customer receives email with portal link + token

### Create a Test Customer (Local)
```bash
bench --site mysite.local set-admin-password admin
# Then in console:
frappe.get_doc({"doctype": "User", "email": "test@customer.com", "first_name": "Test", "send_welcome_email": 0}).insert()
frappe.get_doc({"doctype": "Has Role", "parent": "test@customer.com", "parenttype": "User", "parentfield": "roles", "role": "PMS Customer"}).insert()
frappe.db.commit()
```

### Access Portal as Customer
Token URL format:
```
https://office.enfono.com/next-pms/portal?token=<access_token_from_db>
```
Or log in as the customer user directly — they'll be auto-redirected to `/portal`.

### Reset Admin Password
```bash
bench --site office set-admin-password <new-password>
# Local: bench --site mysite.local set-admin-password admin
```

## Environment Variables & Config

| Config | Location | Purpose |
|--------|----------|---------|
| `push_vapid_private_key` | site_config.json | VAPID private key for Web Push |
| `push_vapid_public_key` | site_config.json | VAPID public key (shared with browser) |
| `push_vapid_email` | site_config.json | Contact email for push service |
| `db_name`, `db_password` | common_site_config.json | Database credentials |
| `redis_cache`, `redis_queue` | common_site_config.json | Redis connection strings |

### Vite Dev Config
File: `frontend/vite.config.js`
- Dev port: 8081
- API proxy: `/api` → `http://localhost:8000`
- Assets proxy: `/assets` → `http://localhost:8000`
- Files proxy: `/files` → `http://localhost:8000`

### Vue Router Base
```javascript
createWebHistory("/next-pms/")
```
All routes are under `/next-pms/`. Frappe's `website_route_rules` in hooks.py maps `/next-pms/*` to serve the SPA.
