/* eslint-disable */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  page.on('request', request => console.log('>>', request.method(), request.url()));
  page.on('response', response => console.log('<<', response.status(), response.url()));
  
  await page.goto('http://localhost:3000/');
  
  await page.evaluate(() => {
    localStorage.setItem('user-storage', JSON.stringify({
      state: {
        user: { id: "1", email: "test@example.com", role: "teacher", full_name: "Test" }
      },
      version: 0
    }));
  });
  
  console.log("CLICKING LOGIN...");
  await page.click('text=Đăng Nhập');
  
  await page.waitForTimeout(3000);
  console.log("FINAL URL:", page.url());
  
  await browser.close();
})();
