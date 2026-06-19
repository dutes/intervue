import { test, expect } from "@playwright/test";
import { startMockSession, chooseTextMode, answerCurrentQuestion } from "./helpers";

test("mock interview runs end-to-end and renders a report", async ({ page }) => {
    await startMockSession(page, 3);
    await chooseTextMode(page);

    // Round 3 is 3 main questions, plus up to a few adaptive follow-ups, then it ends and
    // redirects to the report. Loop with a cap rather than hard-coding the count.
    for (let i = 0; i < 12 && !page.url().includes("/report/"); i++) {
        const box = page.getByPlaceholder(/Type your answer here/);
        const hasQuestion = await box.isVisible().catch(() => false);
        if (!hasQuestion) {
            await page.waitForTimeout(500);
            continue;
        }
        await answerCurrentQuestion(page, `Answer ${i + 1}: I owned the work, made the call, and measured a clear result.`);
        // Mock scoring is local/fast; wait for the next question or the report redirect.
        await page.waitForTimeout(1500);
    }

    await expect(page).toHaveURL(/\/report\//, { timeout: 30_000 });
    await expect(page.getByRole("heading", { name: /Interview Report/ })).toBeVisible();
    // The report shows scores and the verdict section.
    await expect(page.getByText("Top Strengths")).toBeVisible();
    await expect(page.getByText("/ 100").first()).toBeVisible();
});
