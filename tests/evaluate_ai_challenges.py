import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from evaluate_ai_quality import *
if '--live' not in sys.argv:
    raise SystemExit('Pass --live to explicitly authorize fictional-material model calls.')
backend._load_saved_key();tls=ssl.create_default_context(cafile=certifi.where());config={'model':'deepseek-flash'}
rows=[]
def save():Path('output/quality-evaluation/challenges.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
for ident,source in [
 ('weighted_percentage_levels','方法占30%，结果占70%。每个维度先按百分制评价：优秀80至100，合格60至79，不合格0至59，最后按权重计算总分。'),
 ('nested_subcriteria','方法40分，其中设计25分、执行15分；结果60分，其中数据30分、讨论30分。只汇总方法和结果两个大项，子项分数包含在大项内。'),
]:
    row={'id':ident,'source':source};started=time.monotonic()
    try:
        result=rubric_ai.interpret(source,'实验报告','',config,tls)
        expected=[30,70] if ident.startswith('weighted') else [40,60]
        row.update(result=result,passed=result['ready'] and sorted(c['maximum_points'] for c in result['criteria'])==expected)
    except Exception as e:row.update(passed=False,error=str(e))
    row['seconds']=round(time.monotonic()-started,3);rows.append(row);save();print(ident,row['passed'],flush=True)
source='整体评分满分10分，不分维度。先以10分为基础；报告正文明确列出的每一项未完成任务扣2分，整份报告累计最多扣4分；其他内容不影响分数。'
try:
    rubric=rubric_ai.interpret(source,'实验报告','',config,tls)
    for ident,body,expected in [('deduction_cap','未完成任务：A、B、C。',6),('no_deduction','所有任务已完成，没有未完成任务。',10)]:
        row={'id':ident,'source':body,'rubric':rubric,'expected_total':expected};started=time.monotonic()
        try:
            assert rubric['ready'],'细则尚未就绪'
            report={'paragraphs':[{'id':'p1','text':body,'heading':False}], 'assignment':{'id':'challenge','title':'扣分上限测试','assignment_type':'实验报告','instructions':'','rubric':{**rubric,'name':'扣分测试','version':'1'}}}
            result=backend.analyze(report,'deepseek',config,tls)
            row.update(result=result,passed=result['suggested_total']==expected)
        except Exception as e:row.update(passed=False,error=str(e))
        row['seconds']=round(time.monotonic()-started,3);rows.append(row);save();print(ident,row['passed'],flush=True)
except Exception as e:rows.append({'id':'deduction_setup','passed':False,'error':str(e)});save()
