/* Snapshot backups only: the working database always remains on this computer. */
(() => {
 'use strict';
 const host=document.getElementById('settingsSettings');if(!host)return;
 const t=(zh,en)=>globalThis.LabwiseI18n?.locale==='en'?en:zh;
 const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
 const panel=el('article',undefined,'panel settings-note cloud-backup');panel.id='cloudBackupPanel';
 panel.append(el('h2',t('网盘备份','Cloud backups')),el('p',t('备份已保存的原稿、评分、私人笔记和历史。未保存输入、AI 密钥和网盘授权不包含在内。ZIP 未加密，请选择学校允许使用的位置。','Backs up saved originals, scores, private notes and history. Unsaved inputs, AI keys and cloud credentials are excluded. ZIP files are not encrypted; choose an institution-approved location.')));
 panel.append(el('p',t('这是完整快照备份。换电脑后恢复为独立副本；两台电脑上的修改不会自动合并。','These are full snapshots. Restore a separate copy on another computer; changes on two computers are not merged.')));
 const form=el('form'),provider=el('select');provider.id='cloudProvider';
 for(const [value,label]of [['icloud','iCloud Drive'],['onedrive_folder',t('OneDrive 客户端文件夹','OneDrive client folder')],['onedrive',t('OneDrive 账号','OneDrive account')]]){const option=el('option',label);option.value=value;provider.append(option);}
 const label=(text,input)=>{const n=el('label',text);n.append(input);return n;};
 form.append(label(t('备份目标','Backup destination'),provider));
 const folder=el('input');folder.id='cloudFolder';folder.type='text';folder.autocomplete='off';folder.placeholder=t('输入已存在的网盘文件夹绝对路径','Absolute path to an existing cloud folder');
 const folderLabel=label(t('本机网盘文件夹','Local cloud folder'),folder);form.append(folderLabel);
 const interval=el('select');interval.id='cloudInterval';for(const [value,text]of [[0,t('关闭自动备份','Automatic backup off')],[15,t('每 15 分钟','Every 15 minutes')],[60,t('每 60 分钟','Every 60 minutes')]]){const n=el('option',text);n.value=String(value);interval.append(n);}
 form.append(label(t('应用运行时的自动备份','Automatic backups while the app is running'),interval));
 form.append(el('p',t('保存位置不会立即上传。启用定时备份后，应用运行期间按所选间隔备份已保存资料。关闭应用后停止；请先保存批改内容。','Saving a location does not upload immediately. Enabling a schedule authorizes backups of saved data while the app runs. Backups stop when the app closes. Save your review first.')));
 const controls=el('div',undefined,'cloud-actions');
 function button(text,fn){const b=el('button',text);b.type='button';b.addEventListener('click',()=>run(fn));return b;}
 const save=el('button',t('保存备份设置','Save backup settings'));save.type='submit';
 const backup=button(t('立即备份','Back up now'),async()=>{
  if(state.dirty||assignmentEditor.dirty)throw Error(t('请先保存当前修改，再生成备份。','Save your current changes before backing up.'));
  if(changed)throw Error(t('请先保存备份设置。','Save the backup settings first.'));
  const result=await api('cloud/backup',{provider:provider.value});await refresh();
  notice.textContent=result.state==='uploaded'?t('OneDrive 服务已接收上传；另一台电脑仍需下载并校验。','OneDrive has accepted the upload. Another computer must still download and validate it.'):t('已写入本机网盘目录；云端状态请查看 Finder 或网盘客户端。','Written to the local cloud folder. Check Finder or the cloud client for upload status.');
  await loadHistory();
 });
 const list=button(t('查看备份历史','View backup history'),loadHistory);
 const reload=button(t('刷新状态','Refresh status'),()=>refresh(true));controls.append(save,backup,list,reload);form.append(controls);panel.append(form);
 const account=el('div',undefined,'cloud-account'),auth=el('p');auth.id='cloudAuthStatus';
 const connect=button(t('连接 OneDrive','Connect OneDrive'),async()=>{pending=await api('cloud/connect',{});auth.replaceChildren(el('span',t('请在微软官方页面输入验证码：','Enter this code on Microsoft’s official page: ')),el('strong',pending.user_code));const a=el('a',t('打开微软登录页','Open Microsoft sign-in'));a.href=pending.verification_uri;a.target='_blank';a.rel='noopener noreferrer';auth.append(document.createTextNode(' '),a);pollTimer=setTimeout(poll,Math.max(5,pending.interval)*1000);});
 const disconnect=button(t('断开 / 取消授权','Disconnect / cancel sign-in'),async()=>{await api('cloud/disconnect',{});clearTimeout(pollTimer);pending=null;auth.replaceChildren();await refresh();});
 account.append(el('p',t('账号模式使用微软官方登录。此试用版只在内存保管授权，退出应用后需重新连接；未配置微软应用 ID 时请使用客户端文件夹。','Account mode uses Microsoft sign-in. This trial keeps credentials in memory only; reconnect after restarting. If no Microsoft app ID is configured, use a client folder.')),connect,disconnect,auth);panel.append(account);
 const locationInfo=el('p',undefined,'support-path'),summary=el('p'),notice=el('p'),history=el('div',undefined,'cloud-history');
 notice.id='cloudBackupStatus';notice.setAttribute('role','status');notice.setAttribute('aria-live','polite');summary.id='cloudBackupSummary';history.id='cloudBackupHistory';
 panel.append(locationInfo,summary,notice,history,el('p',t('上限：ZIP 64 MiB、展开资料 256 MiB。历史不自动清理，可在网盘中管理。','Limits: ZIP 64 MiB, expanded data 256 MiB. History is not deleted automatically; manage it in your cloud drive.')));host.append(panel);
 let data=null,busy=false,changed=false,pending=null,pollTimer=null;
 function render(){if(!data)return;const p=provider.value,target=data.targets[p],remote=p==='onedrive';folderLabel.hidden=remote;account.hidden=!remote;folder.value=target.folder||'';interval.value=String(target.interval);connect.disabled=busy||!!pending||target.connected||!target.available;disconnect.disabled=busy||(!pending&&!target.connected);backup.disabled=busy||(remote&&(!target.available||!target.connected));
  const format=s=>s?new Date(s).toLocaleString():t('尚无记录','None yet');
  summary.textContent=t('最近成功：','Last successful backup: ')+format(target.last_success)+t('；最近尝试：','; last attempt: ')+format(target.last_attempt)+(remote?(target.connected?t('；已连接','; connected'):t('；需连接账号','; sign-in required')):'');
  locationInfo.textContent=remote?t('目标：OneDrive 的 Labwise 应用文件夹','Destination: Labwise app folder in OneDrive'):target.folder?((p==='icloud'&&target.location_kind==='icloud')?'iCloud Drive: ':t('自选备份目录（请自行确认客户端上传）：','Custom folder (check your cloud client): '))+target.folder:t('尚未配置目录。iCloud Drive 常见位置：','No folder configured. Common iCloud Drive location: ')+data.icloud_suggestion;
  if(target.error)notice.textContent=target.error;
 }
 async function refresh(reset=false){data=await api('cloud/status');if(reset||!changed){changed=false;render();}return data;}
 async function run(fn){if(busy)return;busy=true;panel.setAttribute('aria-busy','true');for(const input of form.elements)input.disabled=true;connect.disabled=disconnect.disabled=true;notice.textContent=t('正在处理，请勿退出应用…','Working. Keep the app running…');try{await fn();}catch(error){notice.textContent=error.message;}finally{busy=false;panel.removeAttribute('aria-busy');for(const input of form.elements)input.disabled=false;if(data){const target=data.targets[provider.value];connect.disabled=!!pending||target.connected||!target.available;disconnect.disabled=!pending&&!target.connected;backup.disabled=provider.value==='onedrive'&&(!target.available||!target.connected);}}}
 form.addEventListener('submit',event=>{event.preventDefault();run(async()=>{data=await api('cloud/configure',{provider:provider.value,folder:folder.value,interval:Number(interval.value)});changed=false;render();notice.textContent=t('备份设置已保存。','Backup settings saved.');});});
 form.addEventListener('input',()=>{changed=true;});
 provider.addEventListener('change',()=>{changed=false;history.replaceChildren();notice.textContent='';render();});
 async function loadHistory(){if(changed)throw Error(t('请先保存备份设置。','Save the backup settings first.'));const p=provider.value,result=await api('cloud/history',{provider:p});history.replaceChildren(el('h3',t('备份历史','Backup history')));if(!result.items.length){history.append(el('p',t('该目标尚无可用备份。','No backups are available at this destination.')));return;}
  for(const item of result.items){const row=el('div',undefined,'cloud-history-row');row.append(el('span',item.name+' · '+(item.size/1048576).toFixed(2)+' MiB'));
   row.append(button(t('恢复为独立副本','Restore separate copy'),async()=>{if(state.dirty||assignmentEditor.dirty)throw Error(t('请先保存当前修改，再恢复备份。','Save current changes before restoring.'));if(!window.confirm(t('将从所选备份建立独立副本，当前工作区保留。副本包含原稿和私人笔记，AI 密钥需重新配置。继续？','Create a separate copy containing originals and private notes? Your current workspace is retained. Configure AI keys again in the copy.')))return;
    const result=await api('cloud/restore',{provider:p,id:item.id});notice.replaceChildren(el('p',t('已建立独立副本，当前工作区未改变。','A separate copy is ready. The current workspace is unchanged.')),el('p',result.directory,'support-path'),el('p',t('关闭当前应用后，在副本目录运行“启动恢复副本.command”。重新配置 AI 密钥后继续；不要在两台电脑同时修改。','Close this app, then run “启动恢复副本.command” in the copy directory. Configure AI keys again before continuing. Avoid editing on both computers at once.')));
   }));history.append(row);
  }
 }
 async function poll(){if(!pending)return;if(busy){pollTimer=setTimeout(poll,5000);return;}try{const result=await api('cloud/poll',{});if(result.state==='connected'){pending=null;auth.textContent=t('OneDrive 已连接。尚未上传资料。','OneDrive connected. No data has been uploaded.');await refresh();}else if(result.state==='pending'){pollTimer=setTimeout(poll,Math.max(5,pending.interval)*1000);}else{pending=null;auth.textContent=t('授权已结束，请重新连接。','Sign-in ended. Connect again.');await refresh();}}catch(error){pending=null;auth.textContent=error.message;await refresh().catch(()=>{});}}
 window.addEventListener('beforeunload',event=>{if(busy){event.preventDefault();event.returnValue='';}});
 refresh().catch(error=>{notice.textContent=error.message;});
})();
