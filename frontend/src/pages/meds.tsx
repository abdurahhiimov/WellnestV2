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
import { medPurpose } from "@/lib/clinical-labels";
import { useI18n } from "@/lib/i18n";
import { useStore } from "@/lib/store";

export function MedsPage() {
  const { t, lang } = useI18n();
  const { data } = useStore();
  if (!data) return null;
  const meds = data.medications || [];

  return (
    <div className="flex flex-1 flex-col gap-6 py-6">
      <h1 className="zh-rise font-semibold text-xl leading-tight">{t("medsTitle")}</h1>
      <Card className="zh-rise zh-rise-1 py-0">
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-6">{t("thMed")}</TableHead>
                <TableHead>{t("thDose")}</TableHead>
                <TableHead className="hidden pr-6 sm:table-cell">{t("thPurpose")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {meds.map((med) => (
                <TableRow key={med.id}>
                  <TableCell className="pl-6">
                    <span className="flex items-center gap-2">
                      <span className="font-medium">{med.name}</span>
                      {med.generic && (
                        <span className="hidden text-muted-foreground text-xs md:inline">
                          {med.generic}
                        </span>
                      )}
                      {med.status !== "active" && (
                        <Badge variant="outline">
                          {med.status === "stopped" ? t("medStopped") : med.status}
                        </Badge>
                      )}
                    </span>
                  </TableCell>
                  <TableCell className="tabular-nums">{med.dose}</TableCell>
                  <TableCell className="hidden pr-6 text-muted-foreground sm:table-cell">
                    {medPurpose(med.purpose, lang)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
