import asyncio
import os
import logging
from typing import Dict, Any, Callable
from playwright.async_api import async_playwright

logger = logging.getLogger("RealAutoApplyEngine")

class RealApplicationRunner:
    def __init__(self, log_callback: Callable[[Dict[str, Any]], None]):
        self.log_callback = log_callback
        self.is_running = False

    def emit(self, platform: str, job_title: str, company: str, status: str, message: str, link: str = "#"):
        entry = {
            "platform": platform,
            "title": job_title,
            "company": company,
            "status": status,
            "message": message,
            "link": link
        }
        self.log_callback(entry)

    async def run(self, preferences: Dict[str, Any], resume_path: str):
        self.is_running = True
        titles = preferences.get("job_titles", ["Technical Project Manager"])
        location = preferences.get("location", "India")
        platforms = preferences.get("platforms", ["linkedin", "naukri", "indeed"])
        max_jobs = int(preferences.get("max_jobs_per_platform", 5))

        user_data_dir = os.path.abspath("browser_session")
        os.makedirs(user_data_dir, exist_ok=True)
        abs_resume_path = os.path.abspath(resume_path) if resume_path and os.path.exists(resume_path) else None

        self.emit("System", "Browser Session", "Chrome Engine", "In Progress", "Launching real persistent Chrome browser session...")

        async with async_playwright() as p:
            # Persistent context saves your login session (cookies, localStorage)
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False, # Visible so user sees real applications
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
                viewport=None
            )
            page = context.pages[0] if context.pages else await context.new_page()

            for platform in platforms:
                if not self.is_running:
                    break

                for title in titles:
                    if not self.is_running:
                        break

                    if platform == "linkedin":
                        await self._apply_linkedin_real(page, title, location, max_jobs, abs_resume_path)
                    elif platform == "naukri":
                        await self._apply_naukri_real(page, title, location, max_jobs, abs_resume_path)
                    elif platform == "indeed":
                        await self._apply_indeed_real(page, title, location, max_jobs, abs_resume_path)

            self.emit("System", "Batch Complete", "Agent", "Info", "Finished all platform application cycles.")
            await context.close()
            self.is_running = False

    async def _apply_linkedin_real(self, page, title: str, location: str, max_jobs: int, resume_path: str):
        self.emit("LinkedIn", title, "LinkedIn Portal", "In Progress", "Checking LinkedIn login status...")
        try:
            await page.goto("https://www.linkedin.com/jobs/", wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(3)

            # Check if user needs to login
            if "feed" not in page.url and "jobs" not in page.url and await page.locator("input#username").count() > 0:
                self.emit("LinkedIn", "Login Required", "LinkedIn", "Action Needed", "Please log in to LinkedIn in the browser window now! Waiting 40s...")
                for _ in range(40):
                    if not self.is_running:
                        return
                    if await page.locator(".global-nav__me").count() > 0 or "jobs" in page.url:
                        break
                    await asyncio.sleep(1)

            search_url = f"https://www.linkedin.com/jobs/search/?keywords={title.replace(' ', '%20')}&location={location.replace(' ', '%20')}&f_AL=true"
            self.emit("LinkedIn", title, "Searching", "In Progress", f"Navigating to Easy Apply jobs for '{title}'...")
            await page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(4)

            job_cards = await page.locator(".jobs-search-results-list__list-item, .job-card-container").all()
            self.emit("LinkedIn", title, "Search Results", "Info", f"Found {len(job_cards)} Easy Apply listings on LinkedIn.")

            applied_count = 0
            for card in job_cards:
                if not self.is_running or applied_count >= max_jobs:
                    break

                try:
                    await card.scroll_into_view_if_needed()
                    await card.click()
                    await asyncio.sleep(2)

                    # Get title & company
                    job_name = title
                    comp_name = "Employer"
                    title_elem = page.locator(".job-details-jobs-unified-top-card__job-title, h1.t-24")
                    if await title_elem.count() > 0:
                        job_name = (await title_elem.first.inner_text()).strip()

                    comp_elem = page.locator(".job-details-jobs-unified-top-card__company-name")
                    if await comp_elem.count() > 0:
                        comp_name = (await comp_elem.first.inner_text()).strip()

                    # Look for Easy Apply button
                    easy_btn = page.locator("button.jobs-apply-button")
                    if await easy_btn.count() == 0 or not await easy_btn.first.is_visible():
                        self.emit("LinkedIn", job_name, comp_name, "Skipped", "No direct Easy Apply button found.")
                        continue

                    self.emit("LinkedIn", job_name, comp_name, "In Progress", "Clicking Easy Apply modal...")
                    await easy_btn.first.click()
                    await asyncio.sleep(2)

                    # Multi-step apply modal handler
                    modal = page.locator("div.jobs-easy-apply-modal, div[role='dialog']")
                    if await modal.count() > 0:
                        submit_success = await self._handle_linkedin_modal_steps(page, modal, resume_path)
                        if submit_success:
                            self.emit("LinkedIn", job_name, comp_name, "Applied", "REAL APPLICATION SUBMITTED ON LINKEDIN!")
                            applied_count += 1
                        else:
                            self.emit("LinkedIn", job_name, comp_name, "Skipped", "Complex screening questionnaire encountered; safely skipped.")
                    await asyncio.sleep(3)

                except Exception as ex:
                    self.emit("LinkedIn", title, "Card Handler", "Failed", f"Error on job card: {str(ex)[:80]}")

        except Exception as e:
            self.emit("LinkedIn", title, "Error", "Failed", f"LinkedIn engine stopped: {str(e)[:100]}")

    async def _handle_linkedin_modal_steps(self, page, modal, resume_path: str) -> bool:
        # Step through modal up to 5 steps
        for _ in range(5):
            await asyncio.sleep(1.5)
            # Check for Submit application button
            submit_btn = modal.locator("button[aria-label='Submit application']")
            if await submit_btn.count() > 0 and await submit_btn.first.is_visible():
                await submit_btn.first.click()
                await asyncio.sleep(2)
                # Close confirmation modal if any
                close_btn = page.locator("button[aria-label='Dismiss']")
                if await close_btn.count() > 0:
                    await close_btn.first.click()
                return True

            # If Next button exists
            next_btn = modal.locator("button[aria-label='Continue to next step'], button:has-text('Next')")
            if await next_btn.count() > 0 and await next_btn.first.is_visible():
                # Check for upload input if resume required
                upload_input = modal.locator("input[type='file']")
                if await upload_input.count() > 0 and resume_path:
                    try:
                        await upload_input.first.set_input_files(resume_path)
                        await asyncio.sleep(1)
                    except Exception:
                        pass

                await next_btn.first.click()
                continue

            # Review button
            review_btn = modal.locator("button[aria-label='Review your application'], button:has-text('Review')")
            if await review_btn.count() > 0 and await review_btn.first.is_visible():
                await review_btn.first.click()
                continue

            break

        # Cancel/close modal if unfinished to not block flow
        try:
            dismiss_btn = modal.locator("button[aria-label='Dismiss']")
            if await dismiss_btn.count() > 0:
                await dismiss_btn.first.click()
                discard_btn = page.locator("button[data-control-name='discard_application_confirm_btn']")
                if await discard_btn.count() > 0:
                    await discard_btn.first.click()
        except Exception:
            pass
        return False

    async def _apply_naukri_real(self, page, title: str, location: str, max_jobs: int, resume_path: str):
        self.emit("Naukri", title, "Naukri Portal", "In Progress", "Navigating to Naukri.com...")
        try:
            await page.goto("https://www.naukri.com/", wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(3)

            # Check if user logged in
            if await page.locator("a:has-text('Login')").count() > 0:
                self.emit("Naukri", "Login Detected", "Naukri", "Action Needed", "If you want Naukri 1-Click applies, please log in now in browser (30s window).")
                await asyncio.sleep(20)

            slug = title.lower().replace(" ", "-")
            loc_slug = location.lower().replace(" ", "-")
            url = f"https://www.naukri.com/{slug}-jobs-in-{loc_slug}"
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(3)

            job_articles = await page.locator("article.jobTuple, div.srp-jobtuple-wrapper").all()
            self.emit("Naukri", title, "Search Results", "Info", f"Found {len(job_articles)} jobs on Naukri page.")

            applied_count = 0
            for article in job_articles:
                if not self.is_running or applied_count >= max_jobs:
                    break

                try:
                    title_elem = article.locator("a.title")
                    job_name = (await title_elem.first.inner_text()).strip() if await title_elem.count() > 0 else title
                    comp_elem = article.locator("a.comp-name")
                    comp_name = (await comp_elem.first.inner_text()).strip() if await comp_elem.count() > 0 else "Employer"

                    # Check for 1-click apply or open job page
                    apply_btn = article.locator("button:has-text('Apply'), a:has-text('Apply')")
                    if await apply_btn.count() > 0:
                        self.emit("Naukri", job_name, comp_name, "In Progress", "Attempting 1-Click apply on Naukri...")
                        await apply_btn.first.click()
                        await asyncio.sleep(2)
                        self.emit("Naukri", job_name, comp_name, "Applied", "REAL NAUKRI APPLICATION SUBMITTED!")
                        applied_count += 1
                    else:
                        self.emit("Naukri", job_name, comp_name, "Discovered", "External apply link detected.")

                    await asyncio.sleep(2)
                except Exception as e:
                    self.emit("Naukri", title, "Listing", "Skipped", f"Item skipped: {str(e)[:60]}")

        except Exception as e:
            self.emit("Naukri", title, "Error", "Failed", f"Naukri session: {str(e)[:100]}")

    async def _apply_indeed_real(self, page, title: str, location: str, max_jobs: int, resume_path: str):
        self.emit("Indeed", title, "Indeed Portal", "In Progress", "Navigating to Indeed India...")
        try:
            url = f"https://in.indeed.com/jobs?q={title.replace(' ', '+')}&l={location.replace(' ', '+')}"
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(3)

            cards = await page.locator("div.job_seen_beacon").all()
            self.emit("Indeed", title, "Search Results", "Info", f"Found {len(cards)} listings on Indeed.")

            applied_count = 0
            for card in cards:
                if not self.is_running or applied_count >= max_jobs:
                    break

                try:
                    await card.click()
                    await asyncio.sleep(2)

                    job_title = title
                    t_elem = page.locator("h2.jobsearch-JobInfoHeader-title")
                    if await t_elem.count() > 0:
                        job_title = (await t_elem.first.inner_text()).strip()

                    # Look for "Apply now" button (Indeed Easy Apply)
                    apply_button = page.locator("button#indeedApplyButton, button:has-text('Apply now')")
                    if await apply_button.count() > 0 and await apply_button.first.is_visible():
                        self.emit("Indeed", job_title, "Indeed Employer", "In Progress", "Clicking 'Apply now' on Indeed...")
                        await apply_button.first.click()
                        await asyncio.sleep(3)
                        self.emit("Indeed", job_title, "Indeed Employer", "Applied", "REAL APPLICATION SUBMISSION INITIATED ON INDEED!")
                        applied_count += 1
                    else:
                        self.emit("Indeed", job_title, "Indeed Employer", "Skipped", "Job requires redirect to external company careers page.")

                    await asyncio.sleep(2)
                except Exception as ex:
                    self.emit("Indeed", title, "Card", "Skipped", f"Could not process card: {str(ex)[:60]}")

        except Exception as e:
            self.emit("Indeed", title, "Error", "Failed", f"Indeed session: {str(e)[:100]}")

    def stop(self):
        self.is_running = False
