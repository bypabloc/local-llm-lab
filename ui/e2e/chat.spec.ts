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

    const textarea = page.getByPlaceholder("Escribí un mensaje...")
    await textarea.fill("Decí 'hola' y nada más.")
    await page.getByRole("button", { name: "Enviar" }).click()

    await expect(page.getByText("Decí 'hola' y nada más.").last()).toBeVisible()

    const assistantMessage = page.locator("text=assistant").locator("..").last()
    await expect(assistantMessage).toBeVisible({ timeout: 60_000 })
    await expect(async () => {
      const text = await assistantMessage.locator("p").innerText()
      expect(text.length).toBeGreaterThan(0)
    }).toPass({ timeout: 60_000 })

    await expect(textarea).toBeEnabled({ timeout: 60_000 })
  })

  test("toggle de device y agent en el sidebar cambian el select", async ({
    page,
  }) => {
    await page.goto("/")

    const selects = page.locator("aside select")
    const deviceSelect = selects.nth(1)
    await deviceSelect.selectOption("cpu")
    await expect(deviceSelect).toHaveValue("cpu")

    const agentSelect = selects.nth(2)
    await agentSelect.selectOption("tars")
    await expect(agentSelect).toHaveValue("tars")
  })

  test("abre y cierra la vista de Bench por clic", async ({ page }) => {
    await page.goto("/")

    await page.getByRole("button", { name: "Bench" }).click()
    await expect(page.getByRole("heading", { name: "Bench" })).toBeVisible()

    await page.getByRole("button", { name: "Cerrar" }).click()
    await expect(page.getByRole("heading", { name: "Bench" })).toBeHidden()
    await expect(page.getByPlaceholder("Escribí un mensaje...")).toBeVisible()
  })

  test("Tailwind compila y aplica estilos reales (no solo CSS plano)", async ({
    page,
  }) => {
    await page.goto("/")

    const sidebarWidth = await page
      .locator("aside")
      .evaluate((el) => getComputedStyle(el).width)
    expect(sidebarWidth).toBe("280px")

    const flexDisplay = await page
      .locator("aside")
      .evaluate((el) => getComputedStyle(el.parentElement!.parentElement!).display)
    expect(flexDisplay).toBe("flex")
  })

  test("Nueva conversación limpia los mensajes", async ({ page }) => {
    await page.goto("/")

    const textarea = page.getByPlaceholder("Escribí un mensaje...")
    await textarea.fill("Decí 'hola' y nada más.")
    await page.getByRole("button", { name: "Enviar" }).click()
    await expect(page.getByText("Decí 'hola' y nada más.").last()).toBeVisible()

    await page.getByRole("button", { name: "Nueva conversación" }).click()
    await expect(page.getByText("Decí 'hola' y nada más.")).toHaveCount(0)
  })

  test("Exportar está deshabilitado sin mensajes y habilitado tras enviar uno", async ({
    page,
  }) => {
    await page.goto("/")

    const exportButton = page.getByRole("button", { name: "Exportar" })
    await expect(exportButton).toBeDisabled()

    const textarea = page.getByPlaceholder("Escribí un mensaje...")
    await textarea.fill("Decí 'hola' y nada más.")
    await page.getByRole("button", { name: "Enviar" }).click()

    await expect(exportButton).toBeEnabled()
  })

  test("Copiar copia la conversación al portapapeles", async ({
    page,
    context,
  }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"])
    await page.goto("/")

    const copyButton = page.getByRole("button", { name: "Copiar" })
    await expect(copyButton).toBeDisabled()

    const textarea = page.getByPlaceholder("Escribí un mensaje...")
    await textarea.fill("Decí 'hola' y nada más.")
    await page.getByRole("button", { name: "Enviar" }).click()

    await expect(copyButton).toBeEnabled()
    await copyButton.click()
    await expect(page.getByRole("button", { name: "Copiado" })).toBeVisible()

    const clipboardText = await page.evaluate(() => navigator.clipboard.readText())
    expect(clipboardText).toContain("Decí 'hola' y nada más.")
  })

  test("la toolbar tiene botones de recargar ventana y reiniciar app", async ({
    page,
  }) => {
    await page.goto("/")

    await expect(page.getByRole("button", { name: "Recargar ventana" })).toBeVisible()
    await expect(page.getByRole("button", { name: "Reiniciar app" })).toBeVisible()
  })

  test("Recargar ventana recarga la página (mensajes se limpian)", async ({
    page,
  }) => {
    await page.goto("/")

    const textarea = page.getByPlaceholder("Escribí un mensaje...")
    await textarea.fill("Decí 'hola' y nada más.")
    await page.getByRole("button", { name: "Enviar" }).click()
    await expect(page.getByText("Decí 'hola' y nada más.").last()).toBeVisible()

    await page.getByRole("button", { name: "Recargar ventana" }).click()
    await page.waitForLoadState("load")

    await expect(page.getByText("Decí 'hola' y nada más.")).toHaveCount(0)
  })
})
