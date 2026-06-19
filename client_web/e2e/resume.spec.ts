import { test, expect } from "@playwright/test";
import { startMockSession, chooseTextMode } from "./helpers";

test("an interview resumes after a page reload", async ({ page }) => {
    await startMockSession(page, 3);
    await chooseTextMode(page);
    await expect(page.getByPlaceholder(/Type your answer here/)).toBeVisible({ timeout: 30_000 });

    const sessionUrl = page.url(); // /session/<id>
    await page.reload();

    // The session is reloaded from the DB and the pending question is re-served — we stay on
    // the same session (not bounced to /new or an error). This also guards the start_round
    // int-coercion fix, since resume reads the persisted session.
    await expect(page).toHaveURL(sessionUrl);
    await chooseTextMode(page); // the chooser reappears after a reload
    await expect(page.getByPlaceholder(/Type your answer here/)).toBeVisible({ timeout: 30_000 });
});
