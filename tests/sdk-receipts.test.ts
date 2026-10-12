import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {decodeLocalnetTransaction} from 'genlayer-js';
import {transactionState} from '../lib/domain';

test('pinned SDK decodes the live creation return value',()=>{
 const raw=JSON.parse(readFileSync('deploy/receipts/create-demo.json','utf8'));
 const decoded=decodeLocalnetTransaction(raw);
 assert.equal(transactionState(decoded),'FINALIZED_SUCCESS');
 // SDK 1.1.8's declarations retain the raw string type after this decoder.
 const result=decoded.consensus_data?.leader_receipt?.[0]?.result as unknown as {payload:{readable:string}};
 assert.ok(result?.payload&&typeof result.payload==='object');
 assert.equal(JSON.parse(result.payload.readable),'league-1');
});

test('pinned SDK exposes the live expected rejection message',()=>{
 const raw=JSON.parse(readFileSync('deploy/wallet-adapter-rejection-check.json','utf8')).receipt;
 const decoded=decodeLocalnetTransaction(raw);
 assert.equal(transactionState(decoded),'FINALIZED_ERROR');
 const result=decoded.consensus_data?.leader_receipt?.[0]?.result as unknown as {payload:string};
 assert.equal(result?.payload,'[EXPECTED] owner configures once');
});
