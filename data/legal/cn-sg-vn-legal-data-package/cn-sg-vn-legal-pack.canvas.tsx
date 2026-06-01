import React from "react";
import {
  Card,
  CardBody,
  CardHeader,
  H1,
  H2,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text
} from "cursor/canvas";

const rows: Array<[string, string, string, string, string]> = [
  ["CN-ENT-001", "China", "enterprise_landing", "Company Law", "samr.gov.cn"],
  ["CN-ENT-002", "China", "enterprise_landing", "Foreign Investment Law", "samr.gov.cn"],
  ["CN-ENT-003", "China", "enterprise_landing", "Market Entity Registration Regulation", "gov.cn"],
  ["CN-TAX-001", "China", "tax", "Enterprise Income Tax Law", "chinatax.gov.cn"],
  ["CN-TAX-002", "China", "tax", "Tax Collection Administration Law", "chinatax.gov.cn"],
  ["CN-TAX-003", "China", "tax", "VAT Law", "chinatax.gov.cn"],
  ["CN-DATA-001", "China", "cross_border_data", "PIPL", "npc.gov.cn"],
  ["CN-DATA-002", "China", "cross_border_data", "Data Security Law", "npc.gov.cn"],
  ["CN-DATA-003", "China", "cross_border_data", "Cybersecurity Law", "npc.gov.cn"],
  ["CN-DATA-004", "China", "cross_border_data", "Data Export Security Assessment Measures", "cac.gov.cn"],
  ["CN-DATA-005", "China", "cross_border_data", "PI Standard Contract Measures", "cac.gov.cn"],
  ["CN-DATA-006", "China", "cross_border_data", "Cross-border Data Flow Provisions", "cac.gov.cn"],
  ["SG-ENT-001", "Singapore", "enterprise_landing", "Companies Act 1967", "sso.agc.gov.sg"],
  ["SG-ENT-002", "Singapore", "enterprise_landing", "Business Names Registration Act", "sso.agc.gov.sg"],
  ["SG-ENT-003", "Singapore", "enterprise_landing", "LLP Act 2005", "sso.agc.gov.sg"],
  ["SG-TAX-001", "Singapore", "tax", "Income Tax Act 1947", "sso.agc.gov.sg"],
  ["SG-TAX-002", "Singapore", "tax", "GST Act 1993", "sso.agc.gov.sg"],
  ["SG-TAX-003", "Singapore", "tax", "Economic Expansion Incentives Act", "sso.agc.gov.sg"],
  ["SG-DATA-001", "Singapore", "cross_border_data", "PDPA 2012", "sso.agc.gov.sg"],
  ["SG-DATA-002", "Singapore", "cross_border_data", "PDP Regulations 2021", "sso.agc.gov.sg"],
  ["SG-DATA-003", "Singapore", "cross_border_data", "PDPC Cross-border Transfer Guide", "pdpc.gov.sg"],
  ["VN-ENT-001", "Vietnam", "enterprise_landing", "Consolidated Law on Enterprises", "congbao.chinhphu.vn"],
  ["VN-ENT-002", "Vietnam", "enterprise_landing", "Consolidated Law on Investment", "congbao.chinhphu.vn"],
  ["VN-TAX-001", "Vietnam", "tax", "Law on Tax Administration 38/2019", "congbao.chinhphu.vn"],
  ["VN-TAX-002", "Vietnam", "tax", "Consolidated Corporate Income Tax Law", "congbao.chinhphu.vn"],
  ["VN-TAX-003", "Vietnam", "tax", "Decree 218/2013 on CIT", "congbao.chinhphu.vn"],
  ["VN-DATA-001", "Vietnam", "cross_border_data", "Cybersecurity Law 24/2018", "congbao.chinhphu.vn"],
  ["VN-DATA-002", "Vietnam", "cross_border_data", "Decree 53/2022", "congbao.chinhphu.vn"],
  ["VN-DATA-003", "Vietnam", "cross_border_data", "Decree 13/2023 on PDP", "congbao.chinhphu.vn"]
];

export default function LegalPackCanvas() {
  return (
    <Stack gap={16}>
      <H1>CN-SG-VN Legal Data Pack</H1>
      <Text tone="secondary">
        Source set built from official legal databases and regulator portals for enterprise landing, tax, and cross-border data compliance.
      </Text>

      <Row gap={8} wrap>
        <Pill tone="neutral">China: 12</Pill>
        <Pill tone="neutral">Singapore: 9</Pill>
        <Pill tone="neutral">Vietnam: 9</Pill>
        <Pill tone="neutral">Total: 30 records</Pill>
      </Row>

      <Row gap={12}>
        <Stat label="Enterprise Landing" value="8" />
        <Stat label="Tax" value="9" />
        <Stat label="Cross-border Data" value="13" />
      </Row>

      <Card>
        <CardHeader>Coverage Snapshot</CardHeader>
        <CardBody>
          <Text>
            All entries are classified with stable IDs for retrieval and include jurisdiction, domain, law title, and official source host.
          </Text>
        </CardBody>
      </Card>

      <H2>Record Index</H2>
      <Table
        headers={["ID", "Country", "Domain", "Law/Regulation", "Official Source"]}
        rows={rows}
        columnAlign={["left", "left", "left", "left", "left"]}
        striped
        stickyHeader
      />
    </Stack>
  );
}
