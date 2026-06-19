import { Page, expect } from "@playwright/test";

/** Start a fresh interview using the keyless mock provider, at the given round (default 3 =
 *  fewest questions, fastest test). Leaves the page on the interview route. */
export async function startMockSession(page: Page, round = 3): Promise<void> {
    await page.goto("/new");
    // A first-run "How Intervue works" modal can appear over the form; close it if present.
    await page.getByRole("button", { name: "Close" }).click({ timeout: 5000 }).catch(() => {});
    await page
        .getByPlaceholder("Paste the job requirements, responsibilities, and qualifications...")
        .fill("Senior QA Engineer for a mobile app — release readiness, test strategy, and CI automation.");
    await page
        .getByPlaceholder("Paste your CV text or upload a file...")
        .fill("QA lead who built a four-layer release-readiness framework and automated CI gates for a large mobile client.");
    // The first <select> is the LLM provider.
    await page.locator("select").first().selectOption("mock");
    await page.getByRole("button", { name: new RegExp(`Round ${round}`) }).click();
    await page.getByRole("button", { name: /Start Interview/ }).click();
    // Mock setup is fast, but allow margin for rubric/persona/CV-analysis steps.
    await page.waitForURL(/\/session\//, { timeout: 60_000 });
}

/** The voice/text chooser appears before the first question (and again after a reload). Pick
 *  Text so the run is deterministic and doesn't depend on audio. */
export async function chooseTextMode(page: Page): Promise<void> {
    // The chooser only appears once the first question has generated, so wait for the button
    // rather than checking immediately (else we race past it and it blocks later clicks).
    await page
        .getByRole("button", { name: /Read questions yourself/ })
        .click({ timeout: 30_000 })
        .catch(() => {});
}

/** Answer the current question. */
export async function answerCurrentQuestion(page: Page, text: string): Promise<void> {
    const box = page.getByPlaceholder(/Type your answer here/);
    await expect(box).toBeVisible({ timeout: 30_000 });
    await box.fill(text);
    await page.getByRole("button", { name: "Submit answer" }).click();
}
