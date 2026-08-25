import { expect, test } from "@playwright/test"

test.describe("chat contra el backend Django real", () => {
  test("carga modelos reales en el selector del sidebar", async ({ page }) => {
    await page.goto("/")

    const select = page.locator("select").first()
    await expect(select.locator("option")).toHaveCount(4)
    await expect(select.locator("option", { hasText: "gemma4-e2b" })).toHaveCount(1)
  })

  test("envía un mensaje por clic y recibe streaming real del modelo", async ({
    page,
  }) => {
    await page.goto("/")

    const textarea = page.locator(".chat-panel__input textarea")
    await textarea.fill("Decí 'hola' y nada más.")
    await page.locator(".chat-panel__input button").click()

    await expect(page.locator(".message--user").last()).toHaveText(
      /Decí 'hola' y nada más\./,
    )

    const assistantMessage = page.locator(".message--assistant").last()
    await expect(assistantMessage).toBeVisible({ timeout: 60_000 })
    await expect(async () => {
      const text = await assistantMessage.locator(".message__content").innerText()
      expect(text.length).toBeGreaterThan(0)
    }).toPass({ timeout: 60_000 })

    await expect(page.locator(".chat-panel__input textarea")).toBeEnabled({
      timeout: 60_000,
    })
  })

  test("toggle de device y agent en el sidebar cambian el select", async ({
    page,
  }) => {
    await page.goto("/")

    const selects = page.locator(".sidebar select")
    const deviceSelect = selects.nth(1)
    await deviceSelect.selectOption("cpu")
    await expect(deviceSelect).toHaveValue("cpu")

    const agentSelect = selects.nth(2)
    await agentSelect.selectOption("tars")
    await expect(agentSelect).toHaveValue("tars")
  })

  test("abre y cierra la vista de Bench por clic", async ({ page }) => {
    await page.goto("/")

    await page.locator(".sidebar__bench-button").click()
    await expect(page.locator(".bench-view")).toBeVisible()
    await expect(page.locator(".bench-view h2")).toHaveText("Bench")

    await page.locator(".bench-view__header button").click()
    await expect(page.locator(".bench-view")).toBeHidden()
    await expect(page.locator(".chat-panel")).toBeVisible()
  })
})
