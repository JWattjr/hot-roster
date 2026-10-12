import {chromium,expect} from '@playwright/test';
import {existsSync,mkdirSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
const base=process.env.HOT_ROSTER_URL??'http://localhost:3120';
const executable=join(process.env.LOCALAPPDATA??'','ms-playwright','chromium-1243','chrome-win64','chrome.exe');
const browser=await chromium.launch({headless:true,...(existsSync(executable)?{executablePath:executable}:{})});
mkdirSync('docs/screenshots',{recursive:true});
const checks:Record<string,unknown>[]=[];
try{
 for(const [name,viewport] of [['desktop',{width:1440,height:960}],['mobile',{width:390,height:844}]] as const){
  const context=await browser.newContext({viewport});const page=await context.newPage();const errors:string[]=[];
  page.on('pageerror',e=>errors.push(e.message));
  for(const route of ['/','/draft','/week','/disputes','/proof','/create']){
   const response=await page.goto(base+route);expect(response?.status()).toBe(200);await expect(page.locator('h1')).toBeVisible();
   const sizes=await page.evaluate(()=>({viewport:innerWidth,width:document.documentElement.scrollWidth}));expect(sizes.width).toBeLessThanOrEqual(sizes.viewport);
   if(route==='/'||route==='/create'||route==='/week')await page.screenshot({path:'docs/screenshots/'+name+'-'+(route==='/'?'season':route.slice(1))+'.png',fullPage:true});
   checks.push({viewport:name,route,status:response?.status(),overflow:false});
  }
  await page.goto(base+'/create');
  await page.getByLabel('League name',{exact:true}).fill('Browser verification league');
  await page.getByLabel('First chart Saturday').fill('2024-05-26');
  await page.getByRole('button',{name:'Create league',exact:true}).click();
  await expect(page.locator('[role=alert]').filter({hasText:/Choose a Saturday|Install MetaMask/})).toContainText('Choose a Saturday');
  await page.getByLabel('First chart Saturday').fill('2024-05-25');
  await page.getByLabel('Optional entry fee · wei').fill('0');
  await page.getByRole('button',{name:'Create league',exact:true}).click();
  await expect(page.locator('[role=alert]').filter({hasText:/Choose a Saturday|Install MetaMask/})).toContainText('Install MetaMask');
  await page.goto(base+'/proof');await expect(page.getByText('Five contracts. Three judgment points.')).toBeVisible();
  expect(await page.locator('.contract-list a').count()).toBe(5);
  await page.getByRole('button',{name:'Connect wallet',exact:true}).click();await expect(page.locator('[role=alert]').filter({hasText:/Choose a Saturday|Install MetaMask/})).toContainText('Install MetaMask');
  await page.reload();await expect(page.locator('h1')).toBeVisible();
  expect(errors).toEqual([]);
  checks.push({viewport:name,formValidation:'Saturday validation works',walletAbsent:'clear error; recorded proof browsable',consoleErrors:errors});
  await context.close();
 }
 writeFileSync('docs/browser-verification.json',JSON.stringify({base,verifiedAt:new Date().toISOString(),checks,limits:['Wallet signing flows require separate live receipts; these browser checks do not fabricate wallet or consensus outcomes.']},null,2));
 console.log(JSON.stringify(checks,null,2));
}finally{await browser.close()}
