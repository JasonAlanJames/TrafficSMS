import { footerSections, mainNavigation } from "./site";

export const navigation = mainNavigation;

export const footerLinks = footerSections.flatMap(
  (section) => section.links ?? []
);