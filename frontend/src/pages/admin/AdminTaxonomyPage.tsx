import { Component, useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { adminGet, adminPatch, adminPost, adminPut } from './adminApi'
import './AdminTaxonomy.css'

type Category = { id:number; code:string; name:string; display_name:string; description?:string; parent_id?:number; color_token:string; sort_order:number; is_active:boolean; is_catalog_visible:boolean; is_searchable:boolean; is_route_eligible:boolean; route_policy:string; route_contexts:string[]; places_count:number }
type Mapping = { id:number; source:string; source_key:string; source_value:string; target_category_id:number; priority:number; confidence:number; active:boolean }
type Conflict = { id:number; place_id:number; place_title?:string; conflict_type:string; severity:string; recommended_category_id?:number }
type Batch = { id:string; status:string; preview?:{ count:number; examples:Array<Record<string,unknown>>; route_conflicts:number } }
type Rule = { id:number; code:string; name_ru:string; severity:string; active:boolean; blocking_publication:boolean; blocking_route_eligibility:boolean }
type TreeNode = Category & { breadcrumb:string; children:TreeNode[] }
type Tab = 'categories'|'tree'|'aliases'|'rules'|'conflicts'|'bulk'|'history'|'routes'
type ItemsPayload<T> = { items?: T[]; total?: number }

const TABS:Array<[Tab,string]> = [['categories','Категории'],['tree','Иерархия'],['aliases','Псевдонимы'],['rules','Правила классификации'],['conflicts','Конфликты'],['bulk','Массовая переклассификация'],['history','История изменений'],['routes','Настройки маршрутов']]
const TAB_KEYS = new Set<Tab>(TABS.map(([key]) => key))
const POLICIES:Record<string,string> = { always_allowed:'Всегда разрешено', allowed_by_context:'По контексту', useful_only:'Только полезные точки', forbidden:'Запрещено', manual_review:'Ручная проверка' }

const policyLabel = (value?: string) => value ? (POLICIES[value] ?? value) : 'Не задано'
const asItems = <T,>(payload: ItemsPayload<T> | T[] | null | undefined): T[] => {
  if (Array.isArray(payload)) return payload
  if (payload && Array.isArray(payload.items)) return payload.items
  return []
}
const errorMessage = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback
const randomId = () => globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`

class TaxonomyErrorBoundary extends Component<{ children: ReactNode }, { error: string | null }> {
  state = { error: null as string | null }
  static getDerivedStateFromError(error: unknown) { return { error: errorMessage(error, 'Не удалось отрисовать страницу таксономии') } }
  render() {
    if (this.state.error) {
      return <div className="taxonomy-page"><div className="admin-state admin-state-error">
        <strong>Страница таксономии упала во frontend.</strong>
        <p>{this.state.error}</p>
        <button className="admin-btn admin-btn-primary" type="button" onClick={() => window.location.reload()}>Перезагрузить</button>
      </div></div>
    }
    return this.props.children
  }
}

export function AdminTaxonomyPage() {
  return <TaxonomyErrorBoundary><AdminTaxonomyContent /></TaxonomyErrorBoundary>
}

function AdminTaxonomyContent() {
  const [params,setParams] = useSearchParams()
  const rawTab = params.get('tab') as Tab | null
  const tab = rawTab && TAB_KEYS.has(rawTab) ? rawTab : 'categories'
  const [categories,setCategories]=useState<Category[]>([])
  const [loading,setLoading]=useState(true)
  const [error,setError]=useState('')

  const load=useCallback(async()=>{
    setLoading(true)
    setError('')
    try {
      const response = await adminGet<ItemsPayload<Category> | Category[]>('/admin/taxonomy/categories?limit=200')
      setCategories(asItems(response))
    } catch(e) {
      setCategories([])
      setError(errorMessage(e, 'Не удалось загрузить категории'))
    } finally {
      setLoading(false)
    }
  },[])

  useEffect(()=>{void load()},[load])

  const setTab = (key: Tab) => {
    const next = new URLSearchParams(params)
    next.set('tab', key)
    setParams(next)
  }

  return <div className="taxonomy-page">
    <header className="admin-page-header">
      <div>
        <h1 className="admin-page-title">Таксономия и качество данных</h1>
        <p className="admin-page-subtitle">Управляемые категории, правила, конфликты и обратимые массовые операции.</p>
      </div>
    </header>
    <nav className="taxonomy-tabs">{TABS.map(([key,label])=><button key={key} type="button" className={`admin-tab ${tab===key?'active':''}`} onClick={()=>setTab(key)}>{label}</button>)}</nav>
    {error && <div className="admin-state admin-state-error"><strong>Не удалось загрузить базовые категории.</strong><p>{error}</p><button className="admin-btn" type="button" onClick={()=>void load()}>Повторить</button></div>}
    {loading ? <div className="admin-state">Загружаем таксономию…</div> : <>
      {tab==='categories'&&<Categories rows={categories} reload={load}/>} {tab==='tree'&&<Tree/>} {tab==='aliases'&&<Mappings rows={categories} alias/>} {tab==='rules'&&<Rules rows={categories}/>} {tab==='conflicts'&&<Conflicts rows={categories}/>} {tab==='bulk'&&<Bulk rows={categories}/>} {tab==='history'&&<History/>} {tab==='routes'&&<Routes rows={categories} reload={load}/>}    </>}
  </div>
}

function Categories({rows,reload}:{rows:Category[];reload:()=>Promise<void>}) {
  const [search,setSearch]=useState('')
  const [edit,setEdit]=useState<Category|null|undefined>()
  const filtered=useMemo(()=>rows.filter(r=>`${r.display_name ?? ''} ${r.code ?? ''}`.toLowerCase().includes(search.toLowerCase())),[rows,search])
  return <section><div className="taxonomy-toolbar"><input placeholder="Поиск по названию или коду" value={search} onChange={e=>setSearch(e.target.value)}/><button className="admin-btn admin-btn-primary" type="button" onClick={()=>setEdit(null)}>Создать категорию</button></div>
    {!filtered.length ? <div className="admin-state">Категорий нет или они не подходят под фильтр</div> : <>
      <div className="taxonomy-table admin-table-wrap"><table className="admin-table"><thead><tr><th>Категория</th><th>Родитель</th><th>Каталог</th><th>Маршруты</th><th>Мест</th><th>Действия</th></tr></thead><tbody>{filtered.map(r=><tr key={r.id}><td><strong>{r.display_name || r.name || r.code}</strong><small>{r.description||'Описание не задано'}</small></td><td>{rows.find(p=>p.id===r.parent_id)?.display_name||'Корневая'}</td><td>{r.is_catalog_visible?'Показывается':'Скрыта'}</td><td>{policyLabel(r.route_policy)}</td><td>{r.places_count ?? 0}</td><td className="admin-actions-cell"><button className="admin-btn admin-btn-sm" type="button" onClick={()=>setEdit(r)}>Редактировать</button><button className="admin-btn admin-btn-sm" type="button" onClick={async()=>{await adminPatch(`/admin/taxonomy/categories/${r.id}`,{is_active:!r.is_active});await reload()}}>{r.is_active?'Архивировать':'Восстановить'}</button></td></tr>)}</tbody></table></div>
      <div className="taxonomy-mobile-list">{filtered.map(r=><article className="taxonomy-card" key={r.id}><div><strong>{r.display_name || r.name || r.code}</strong><span>{policyLabel(r.route_policy)}</span></div><p>{r.description||'Описание не задано'}</p><div className="taxonomy-card-actions"><button className="admin-btn" type="button" onClick={()=>setEdit(r)}>Редактировать</button><button className="admin-btn" type="button" onClick={async()=>{await adminPatch(`/admin/taxonomy/categories/${r.id}`,{is_active:!r.is_active});await reload()}}>{r.is_active?'В архив':'Восстановить'}</button></div></article>)}</div>
    </>}
    {edit!==undefined&&<CategoryForm row={edit} rows={rows} close={()=>setEdit(undefined)} saved={reload}/>}</section>
}

function CategoryForm({row,rows,close,saved}:{row:Category|null;rows:Category[];close:()=>void;saved:()=>Promise<void>}) {
  const [name,setName]=useState(row?.name||'')
  const [code,setCode]=useState(row?.code||'')
  const [description,setDescription]=useState(row?.description||'')
  const [parent,setParent]=useState(row?.parent_id?.toString()||'')
  const [policy,setPolicy]=useState(row?.route_policy||'manual_review')
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const submit=async(e:FormEvent)=>{e.preventDefault();setBusy(true);setError('');const body={name,code,description:description||null,parent_id:parent?Number(parent):null,route_policy:policy,route_contexts:[],is_catalog_visible:true,is_searchable:true,is_route_eligible:policy!=='forbidden',color_token:row?.color_token||'category-default',sort_order:row?.sort_order||0};try{if(row)await adminPatch(`/admin/taxonomy/categories/${row.id}`,body);else await adminPost('/admin/taxonomy/categories',body);await saved();close()}catch(x){setError(errorMessage(x,'Не удалось сохранить'))}finally{setBusy(false)}}
  return <div className="admin-dialog-backdrop"><form className="admin-dialog taxonomy-dialog" onSubmit={submit}><h3>{row?'Редактировать категорию':'Новая категория'}</h3>{error&&<p className="admin-error-text">{error}</p>}<label className="admin-field">Название на русском<input required value={name} onChange={e=>setName(e.target.value)}/></label><label className="admin-field">Внутренний код<input required disabled={Boolean(row)} pattern="[a-z0-9_]+" value={code} onChange={e=>setCode(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g,'_'))}/></label><label className="admin-field">Описание<textarea value={description} onChange={e=>setDescription(e.target.value)}/></label><label className="admin-field">Родитель<select value={parent} onChange={e=>setParent(e.target.value)}><option value="">Корневая</option>{rows.filter(x=>x.id!==row?.id).map(x=><option key={x.id} value={x.id}>{x.display_name || x.name || x.code}</option>)}</select></label><label className="admin-field">Политика маршрутов<select value={policy} onChange={e=>setPolicy(e.target.value)}>{Object.entries(POLICIES).map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label><div className="taxonomy-dialog-actions"><button type="button" className="admin-btn" onClick={close}>Отмена</button><button className="admin-btn admin-btn-primary" disabled={busy}>{busy?'Сохраняем…':'Сохранить'}</button></div></form></div>
}

function Tree(){
  const [tree,setTree]=useState<TreeNode[]>([])
  const [loading,setLoading]=useState(true)
  const [error,setError]=useState('')
  const [drag,setDrag]=useState<number|null>(null)
  const load=useCallback(async()=>{setLoading(true);setError('');try{setTree(asItems(await adminGet<TreeNode[] | ItemsPayload<TreeNode>>('/admin/taxonomy/tree')))}catch(e){setTree([]);setError(errorMessage(e,'Не удалось загрузить дерево'))}finally{setLoading(false)}},[])
  useEffect(()=>{void load()},[load])
  const flat=flatten(tree)
  const move=(parent:number|null)=>{if(drag===null||drag===parent)return;setTree(rebuild(flat.map(x=>x.id===drag?{...x,parent_id:parent||undefined}:x)));setDrag(null)}
  if (loading) return <div className="admin-state">Загружаем дерево…</div>
  if (error) return <div className="admin-state admin-state-error">{error}<button className="admin-btn" type="button" onClick={()=>void load()}>Повторить</button></div>
  return <section className="taxonomy-split"><div className="admin-filter-card"><div className="taxonomy-root-drop" onDragOver={e=>e.preventDefault()} onDrop={()=>move(null)}>Перетащить в корень</div><TreeItems nodes={tree} setDrag={setDrag} move={move}/><button className="admin-btn admin-btn-primary" type="button" onClick={async()=>{await adminPut('/admin/taxonomy/tree',{nodes:flatten(tree).map(({id,parent_id,sort_order})=>({id,parent_id:parent_id||null,sort_order}))});await load()}}>Сохранить дерево</button></div><aside className="admin-help-panel"><strong>Предпросмотр</strong>{flat.map(x=><p className="admin-muted" key={x.id}>{x.breadcrumb}</p>)}</aside></section>
}
function TreeItems({nodes,setDrag,move}:{nodes:TreeNode[];setDrag:(id:number|null)=>void;move:(id:number)=>void}){return <div className="taxonomy-tree">{nodes.map(n=><div className="taxonomy-tree-node" key={n.id}><button type="button" draggable onDragStart={()=>setDrag(n.id)} onDragEnd={()=>setDrag(null)} onDragOver={e=>e.preventDefault()} onDrop={()=>move(n.id)}>{n.display_name || n.name || n.code}<span>{n.children?.length ?? 0} дочерних</span></button>{(n.children?.length ?? 0)>0&&<TreeItems nodes={n.children} setDrag={setDrag} move={move}/>}</div>)}</div>}
function flatten(nodes:TreeNode[],parent:number|null=null,crumbs:string[]=[]):TreeNode[]{return nodes.flatMap((n,i)=>{const label=n.display_name || n.name || n.code;const x={...n,children:n.children??[],parent_id:parent||undefined,sort_order:i,breadcrumb:[...crumbs,label].join(' / ')};return[x,...flatten(n.children??[],n.id,[...crumbs,label])]})}
function rebuild(rows:TreeNode[]):TreeNode[]{const map=new Map(rows.map(x=>[x.id,{...x,children:[] as TreeNode[]}]));const roots:TreeNode[]=[];map.forEach(x=>{const p=x.parent_id?map.get(x.parent_id):undefined;if(p)p.children.push(x);else roots.push(x)});return roots}

function Mappings({rows,alias=false}:{rows:Category[];alias?:boolean}){
  const [items,setItems]=useState<Mapping[]>([])
  const [source,setSource]=useState(alias?'text_alias':'osm')
  const [key,setKey]=useState(alias?'__title__':'amenity')
  const [value,setValue]=useState('')
  const [target,setTarget]=useState('')
  const [loading,setLoading]=useState(true)
  const [error,setError]=useState('')
  const load=useCallback(async()=>{setLoading(true);setError('');try{const all=asItems(await adminGet<ItemsPayload<Mapping> | Mapping[]>('/admin/taxonomy/mappings?limit=300'));setItems(all.filter(x=>alias?x.source==='text_alias':x.source!=='text_alias'))}catch(e){setItems([]);setError(errorMessage(e,'Не удалось загрузить правила'))}finally{setLoading(false)}},[alias])
  useEffect(()=>{void load()},[load])
  const submit=async(e:FormEvent)=>{e.preventDefault();await adminPost('/admin/taxonomy/mappings',{source,source_key:key,source_value:value,target_category_id:Number(target),priority:100,confidence:1,active:true,conditions:{},fallback:false});setValue('');await load()}
  return <section>{error&&<div className="admin-state admin-state-error">{error}</div>}<form className="admin-filter-card taxonomy-mapping-form" onSubmit={submit}><label className="admin-field">Источник<select value={source} onChange={e=>setSource(e.target.value)}>{alias?<option value="text_alias">Текстовый псевдоним</option>:<><option value="osm">OpenStreetMap</option><option value="wikidata">Wikidata</option><option value="legacy">Старая категория</option><option value="import">Источник импорта</option></>}</select></label><label className="admin-field">Ключ<input value={key} onChange={e=>setKey(e.target.value)}/></label><label className="admin-field">Значение<input required value={value} onChange={e=>setValue(e.target.value)}/></label><label className="admin-field">Категория<select required value={target} onChange={e=>setTarget(e.target.value)}><option value="">Выберите</option>{rows.filter(x=>x.is_active).map(x=><option key={x.id} value={x.id}>{x.display_name || x.name || x.code}</option>)}</select></label><button className="admin-btn admin-btn-primary">Добавить правило</button></form>{loading?<div className="admin-state">Загружаем правила…</div>:<div className="taxonomy-rule-list">{items.map(x=><article className="taxonomy-card" key={x.id}><strong>{x.source}: {x.source_key}={x.source_value}</strong><span>→ {rows.find(r=>r.id===x.target_category_id)?.display_name||'Категория недоступна'}</span><button className="admin-btn" type="button" onClick={async()=>{await adminPatch(`/admin/taxonomy/mappings/${x.id}`,{active:!x.active});await load()}}>{x.active?'Отключить':'Включить'}</button></article>)}</div>}</section>
}

function Rules({rows}:{rows:Category[]}){
  const [rules,setRules]=useState<Rule[]>([])
  const [error,setError]=useState('')
  const load=useCallback(async()=>{setError('');try{setRules(asItems(await adminGet<Rule[] | ItemsPayload<Rule>>('/admin/quality/rules')))}catch(e){setRules([]);setError(errorMessage(e,'Не удалось загрузить правила качества'))}},[])
  useEffect(()=>{void load()},[load])
  return <section><Mappings rows={rows}/><h2 className="admin-section-title">Правила качества данных</h2>{error&&<div className="admin-state admin-state-error">{error}</div>}<div className="taxonomy-rule-list">{rules.map(r=><article className="taxonomy-card" key={r.id}><div><strong>{r.name_ru}</strong><span>{r.blocking_publication?'Блокирует публикацию':'Рекомендация'} · {r.blocking_route_eligibility?'Блокирует маршрут':'Не блокирует маршрут'}</span></div><button className="admin-btn" type="button" onClick={async()=>{await adminPatch(`/admin/quality/rules/${r.id}`,{active:!r.active});await load()}}>{r.active?'Отключить':'Включить'}</button></article>)}</div></section>
}

function Conflicts({rows}:{rows:Category[]}){
  const [items,setItems]=useState<Conflict[]>([])
  const [error,setError]=useState('')
  const load=useCallback(async()=>{setError('');try{setItems(asItems(await adminGet<ItemsPayload<Conflict> | Conflict[]>('/admin/taxonomy/conflicts?limit=50')))}catch(e){setItems([]);setError(errorMessage(e,'Не удалось загрузить конфликты'))}},[])
  useEffect(()=>{void load()},[load])
  const resolve=async(x:Conflict,action:string,category?:number)=>{await adminPost(`/admin/taxonomy/conflicts/${x.id}/resolve`,{action,category_id:category||x.recommended_category_id});await load()}
  if (error) return <div className="admin-state admin-state-error">{error}</div>
  return items.length===0?<div className="admin-state">Активных конфликтов нет</div>:<div className="taxonomy-conflicts">{items.map(x=><article className="taxonomy-card taxonomy-conflict" key={x.id}><div><span className="admin-badge">{x.severity==='critical'?'Критично':'Проверить'}</span><strong>{x.place_title||`Место #${x.place_id}`}</strong><p>{x.conflict_type}</p></div><div className="taxonomy-card-actions"><button className="admin-btn admin-btn-primary" type="button" disabled={!x.recommended_category_id} onClick={()=>void resolve(x,'accept')}>Принять</button><select defaultValue="" onChange={e=>e.target.value&&void resolve(x,'choose',Number(e.target.value))}><option value="">Другая категория</option>{rows.filter(r=>r.is_active).map(r=><option key={r.id} value={r.id}>{r.display_name || r.name || r.code}</option>)}</select><button className="admin-btn" type="button" onClick={()=>void resolve(x,'defer')}>Отложить</button><button className="admin-btn" type="button" onClick={()=>void resolve(x,'enrich')}>На обогащение</button></div></article>)}</div>
}

function Bulk({rows}:{rows:Category[]}){
  const [city,setCity]=useState('')
  const [old,setOld]=useState('')
  const [target,setTarget]=useState('')
  const [routes,setRoutes]=useState(false)
  const [batch,setBatch]=useState<Batch|null>(null)
  const [error,setError]=useState('')
  const preview=async()=>{setError('');try{setBatch(await adminPost<Batch>('/admin/taxonomy/bulk/preview',{filters:{city_slug:city||undefined,category_id:old?Number(old):undefined},target_category_id:Number(target),use_rule_engine:false,update_route_eligibility:routes,idempotency_key:randomId(),limit:10000}))}catch(e){setError(errorMessage(e,'Не удалось выполнить dry-run'))}}
  const examples = batch?.preview?.examples ?? []
  return <section>{error&&<div className="admin-state admin-state-error">{error}</div>}<div className="admin-filter-card"><div className="admin-filter-grid"><label className="admin-field">Город<input value={city} onChange={e=>setCity(e.target.value)} placeholder="slug города"/></label><label className="admin-field">Текущая категория<select value={old} onChange={e=>setOld(e.target.value)}><option value="">Любая</option>{rows.map(r=><option key={r.id} value={r.id}>{r.display_name || r.name || r.code}</option>)}</select></label><label className="admin-field">Новая категория<select value={target} onChange={e=>setTarget(e.target.value)}><option value="">Выберите</option>{rows.filter(r=>r.is_active).map(r=><option key={r.id} value={r.id}>{r.display_name || r.name || r.code}</option>)}</select></label><label className="taxonomy-check"><input type="checkbox" checked={routes} onChange={e=>setRoutes(e.target.checked)}/> Обновить route eligibility</label></div><button className="admin-btn admin-btn-primary" type="button" disabled={!target} onClick={()=>void preview()}>Обязательный dry-run</button></div>{batch&&<div className="admin-detail-panel"><h2>{batch.preview?.count ?? 0} мест будет изменено</h2><p>Конфликтов маршрутов: {batch.preview?.route_conflicts ?? 0}</p><div className="taxonomy-examples">{examples.slice(0,10).map((x,i)=><div key={i}><strong>{String(x.title ?? 'Без названия')}</strong><span>{String(x.old_category||'Без категории')} → {String(x.new_category ?? 'Не задано')}</span></div>)}</div><div className="admin-sticky-actions"><span>Пакет {batch.id.slice(0,8)}</span>{batch.status==='preview'&&<button className="admin-btn admin-btn-primary" type="button" onClick={async()=>setBatch(await adminPost<Batch>('/admin/taxonomy/bulk/apply',{batch_id:batch.id}))}>Применить</button>}{batch.status==='applied'&&<button className="admin-btn admin-btn-danger" type="button" onClick={async()=>setBatch(await adminPost<Batch>(`/admin/taxonomy/bulk/${batch.id}/rollback`))}>Откатить</button>}</div></div>}</section>
}
function History(){return <div className="admin-help-panel"><h2>История изменений</h2><p>Ручные решения и массовые пакеты записываются с old/new значениями, actor и batch ID.</p><Link className="admin-btn admin-btn-primary" to="/admin/audit?entity_type=category">Открыть аудит</Link></div>}
function Routes({rows,reload}:{rows:Category[];reload:()=>Promise<void>}){return <div className="taxonomy-rule-list">{rows.map(r=><article className="taxonomy-card" key={r.id}><div><strong>{r.display_name || r.name || r.code}</strong><span>{r.is_catalog_visible?'В каталоге':'Скрыта в каталоге'}</span></div><select value={r.route_policy} onChange={async e=>{await adminPatch(`/admin/taxonomy/categories/${r.id}`,{route_policy:e.target.value,is_route_eligible:e.target.value!=='forbidden'});await reload()}}>{Object.entries(POLICIES).map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></article>)}</div>}
