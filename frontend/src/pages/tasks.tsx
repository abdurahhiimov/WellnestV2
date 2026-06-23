import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { TaskStatusControls } from "@/components/task-status-controls";
import { taskCategory } from "@/lib/clinical-labels";
import { useI18n } from "@/lib/i18n";
import { useStore } from "@/lib/store";

export function TasksPage() {
  const { t, lang } = useI18n();
  const { data } = useStore();
  if (!data) return null;
  const tasks = data.tasks_board || data.tasks_open || [];

  return (
    <div className="flex flex-1 flex-col gap-6 py-6">
      <h1 className="zh-rise font-semibold text-xl leading-tight">{t("tasksTitle")}</h1>
      {tasks.length === 0 ? (
        <Empty className="border border-dashed py-12">
          <EmptyHeader>
            <EmptyTitle>{t("noTasks")}</EmptyTitle>
            <EmptyDescription> </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <Card className="zh-rise zh-rise-1 py-0">
          <CardContent className="px-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-6">{t("thTask")}</TableHead>
                  <TableHead>{t("thPriority")}</TableHead>
                  <TableHead>{t("thStatus")}</TableHead>
                  <TableHead className="hidden pr-6 sm:table-cell">{t("thCategory")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tasks.map((task) => (
                  <TableRow key={task.id}>
                    <TableCell className="pl-6 font-medium">{task.title_ru}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          task.priority === "urgent"
                            ? "destructive"
                            : task.priority === "high"
                              ? "default"
                              : "secondary"
                        }
                      >
                        {task.priority === "urgent"
                          ? t("urgent")
                          : task.priority === "high"
                            ? t("highP")
                            : t("normalP")}
                      </Badge>
                    </TableCell>
                    <TableCell className="min-w-[240px]">
                      <TaskStatusControls status={task.status} taskId={task.id} />
                    </TableCell>
                    <TableCell className="hidden pr-6 text-muted-foreground sm:table-cell">
                      {taskCategory(task.category, lang)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
