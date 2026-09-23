export const dictionaries = {
 en: {title:'Transaction network', subtitle:'AML investigation workspace', run:'Run analysis', running:'Analyzing…', folder:'Input folder', search:'Search exact gid', find:'Find', missing:'Account not found', nodes:'Accounts', edges:'Connections', seeds:'Seed accounts', time:'Execution', priority:'Priority', cluster:'Cluster', all:'All clusters', role:'Role', color:'Color by', overview:'Full network', neighborhood:'Selected neighborhood', reset:'Fit view', hint:'Scroll to zoom · drag to pan · click an account to select', empty:'Load the three parquet files from your input folder to explore the network.', hover:'Hover an account to inspect its evidence', review:'Structural hypotheses for analyst review.', incoming:'Observed incoming', outgoing:'Observed outgoing', depth:'Depth', seedWarning:'Seed account: incoming flow is incomplete.', boundaryWarning:'Depth-4 boundary: outgoing flow may be truncated.', top:'Priority accounts', exports:'CSV exports', failed:'Analysis failed', networkError:'Cannot reach the Python backend', details:'Account evidence', language:'Language', seconds:'s', zoomIn:'Zoom in', zoomOut:'Zoom out'},
 ru: {title:'Граф переводов', subtitle:'Рабочее место AML-аналитика', run:'Запустить анализ', running:'Анализ…', folder:'Папка входных данных', search:'Поиск по точному gid', find:'Найти', missing:'Счёт не найден', nodes:'Счета', edges:'Связи', seeds:'Seed-счета', time:'Время расчёта', priority:'Приоритет', cluster:'Кластер', all:'Все кластеры', role:'Роль', color:'Цвет узлов', overview:'Вся сеть', neighborhood:'Окружение выбранного узла', reset:'Вместить граф', hint:'Колесо — масштаб · перетаскивание — сдвиг · нажатие — выбор счёта', empty:'Загрузите три файла parquet из папки входных данных для просмотра сети.', hover:'Наведите курсор на счёт для просмотра обоснования', review:'Структурные гипотезы для проверки аналитиком.', incoming:'Наблюдаемый входящий поток', outgoing:'Наблюдаемый исходящий поток', depth:'Глубина', seedWarning:'Seed-счёт: входящий поток неполный.', boundaryWarning:'Граница глубины 4: исходящий поток может быть обрезан.', top:'Приоритетные счета', exports:'Экспорт CSV', failed:'Ошибка анализа', networkError:'Нет соединения с Python-сервером', details:'Обоснование по счёту', language:'Язык', seconds:'с', zoomIn:'Увеличить', zoomOut:'Уменьшить'}
};
export const roles = {
 en:{coordinator:'Coordinator',consolidator:'Consolidator',distributor:'Distributor',transit:'Transit',terminal:'Terminal',peripheral:'Peripheral'},
 ru:{coordinator:'Координатор',consolidator:'Консолидатор',distributor:'Распределитель',transit:'Транзит',terminal:'Конечный получатель',peripheral:'Периферия'}
};
export const colors = {coordinator:'#ef6464',consolidator:'#f4af53',distributor:'#5cce96',transit:'#69aefa',terminal:'#be9bed',peripheral:'#75869e'};
export function evidence(n, lang) {
 if(lang==='en') return n.evidence;
 switch(n.role){
 case 'coordinator': return `Seed-счёт с наибольшей наблюдаемой связностью среди seed-счетов: ${n.counterparty_count} контрагентов.`;
 case 'consolidator': return `Получает средства от ${n.n_senders} отправителей; наблюдаемый входящий поток выше исходящего.`;
 case 'distributor': return `Отправляет средства ${n.n_receivers} получателям; наблюдаемый исходящий поток выше входящего.`;
 case 'transit': return `Коэффициент пропуска ${n.pass_through_ratio.toFixed(2)}; есть входящие и исходящие связи.`;
 case 'terminal': return `Нет наблюдаемых исходящих связей; получено ${n.in_amount.toLocaleString('ru-RU')} KZT.`;
 default: return n.is_depth4_boundary ? 'Глубина 4 — граница графа; статус конечного получателя неизвестен.' : 'Структурное правило роли не сработало.';
 }
}
