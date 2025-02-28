from datetime import date

from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify
from treebeard.exceptions import InvalidPosition
from treebeard.mp_tree import MP_Node


# Note PEP-8 naming conventions for class names apply. So use the singular and CamelCase


class City(models.Model):
    class Meta:
        verbose_name = "Kommune"
        verbose_name_plural = "Kommunen"

    draft_mode = models.BooleanField(
        "Entwurfs-Modus",
        default=True,
        help_text=(
            "Im Entwurfs-Modus wird ist die Kommune für normale Besucher im Frontend unsichtbar."
            " Nur wenn im gleichen Browser ein User im Admin angemeldet ist, wird sie angezeigt."
        ),
    )

    name = models.CharField("Name", max_length=255)
    zipcode = models.CharField("PLZ", max_length=5)
    url = models.URLField("Homepage", blank=True)

    resolution_date = models.DateField(
        "Datum des Klimaneutralitäts-Beschlusses",
        blank=True,
        null=True,
    )

    target_year = models.IntegerField(
        "Zieljahr Klimaneutralität", blank=True, null=True, help_text="z.B. 2035"
    )

    introduction = models.TextField(
        "Einleitung",
        blank=True,
        help_text="""
            <p>Eine kurze Beschreibung der Situation in der Kommune.</p>
            <p>Kann in einer Übersicht aller Kommunen dargestellt werden.</p>
            <p>Deswegen möglichst kurz und ohne Formatierungen. Fett, Kursiv, Links, etc. sind okay.</p>
        """,
    )

    co2e_budget = models.IntegerField(
        "CO2e Budget [Mio Tonnen]",
        blank=True,
        default=0,
        help_text="Derzeit nicht genutzt.",
    )

    assessment_administration = models.TextField(
        "Bewertung Verwaltung",
        blank=True,
        help_text="""
            <p>Wie bewertet ihr die Nachhaltigkeitsarchitektur der Verwaltung?</p>
            <p>Die Checkliste hilft dabei, die Übersicht zu behalten.
            Es ist noch nicht klar, ob die Checkliste selber so angezeigt werden kann.
            Dieser Text sollte sie also zusammenfassen.</p>
            <p>Derzeit findest Du die Checkliste nur in der Master Struktur.</p>
        """,
    )

    assessment_action_plan = models.TextField(
        "Bewertung Klimaaktionsplan",
        blank=True,
        help_text="""
            <p>Eine einleitende Übersicht in die Bewertung des Klimaaktionsplans der Kommune.</p>
            <p>Hier könnt Ihr zusammenfassen, was ihr als Ganzes von dem Plan haltet.</p>
            <p>Auf Sektorebene und bis zu den einzelnen Maßnahmen könnt Ihr weiter Details ergänzen.</p>""",
    )

    assessment_status = models.TextField(
        "Bewertung Umsetzungsstand",
        blank=True,
        help_text="""
            <p>Eine einleitende Übersicht in die Bewertung des Umsetzungsstandes.</p>
            <p>Hält die Kommune sich im Wesentlichen an ihren eigenen Plan?</p>
            <p>Auf Sektorebene und bis zu den einzelnen Maßnahmen könnt Ihr weiter Details ergänzen.</p>""",
    )

    last_update = models.DateField("Letzte Aktualisierung", auto_now=True)

    contact_name = models.CharField(
        "Kontakt Name",
        max_length=255,
        blank=True,
        help_text=(
            "Name des Lokalteams oder einer Ansprechperson aus dem Lokalteam, das dieses Monitoring"
            " betreibt."
        ),
    )
    contact_email = models.EmailField(
        "Kontakt E-Mail",
        blank=True,
        help_text="E-Mail Adresse, über die das Lokalteam erreicht werden kann.",
    )

    def __str__(self) -> str:
        return self.zipcode + " " + self.name

    slug = models.SlugField(
        "slug",
        max_length=255,
        unique=True,
        editable=False,
    )

    def clean(self):
        """Set / update the slug on every validation. (Done by admin before `save()`)"""
        self.slug = slugify(self.name)

    def validate_unique(self, exclude=None):
        """
        Add slug to fields to validate uniqueness and convert a slug error to non-field error.

        This is necessary, because `editable=False` excludes the field from validation
        and cannot handle field-based validation errors.
        """
        exclude.remove("slug")
        try:
            super().validate_unique(exclude=exclude)
        except ValidationError as e:
            msgs = e.message_dict
            slug_errors = msgs.pop("slug", None)
            if slug_errors:
                slug_errors.append(
                    "Der Name der Kommune wird in der URL als '%(slug)s' geschrieben. Das"
                    " kollidiert mit einer anderen Stadt." % {"slug": self.slug}
                )
                if not NON_FIELD_ERRORS in msgs:
                    msgs[NON_FIELD_ERRORS] = []
                msgs[NON_FIELD_ERRORS].extend(slug_errors)
            raise ValidationError(msgs)


class CapChecklist(models.Model):
    class Meta:
        verbose_name = "KAP Checkliste"

    city = models.OneToOneField(
        City,
        models.PROTECT,
        related_name="cap_checklist",
    )

    cap_exists = models.BooleanField("Gibt es einen KAP?", default=False)
    target_date_exists = models.BooleanField(
        "Ist im KAP ein Zieljahr der Klimaneutralität hinterlegt und wurde das vom höchsten"
        " kommunalen Gremium beschlossen?",
        default=False,
    )
    based_on_remaining_co2_budget = models.BooleanField(
        "Sind die Einsparziele im KAP auf Grundlage des Restbudgets berechnet?",
        default=False,
    )
    sectors_of_climate_vision_used = models.BooleanField(
        "Bilanziert der KAP in den Sektoren der Klimavision (inkl. LULUCF und Landwirtschaft)",
        default=False,
    )
    scenario_for_climate_neutrality_till_2035_exists = models.BooleanField(
        "Enthält der KAP ein Szenario mit dem Ziel Klimaneutralität bis 2035?",
        default=False,
    )
    scenario_for_business_as_usual_exists = models.BooleanField(
        "Ist ein Trendszenario hinterlegt (wie entwickeln sich die THG-Emissionen, wenn alles so"
        " weiterläuft wie bisher)?",
        default=False,
    )
    annual_costs_are_specified = models.BooleanField(
        "Sind die jährlichen Kosten und der jährliche Personalbedarf der Maßnahmen ausgewiesen?",
        default=False,
    )
    tasks_are_planned_yearly = models.BooleanField(
        "Haben die Maßnahmen eine jahresscharfe Planung?", default=False
    )
    tasks_have_responsible_entity = models.BooleanField(
        "Sind verantwortliche Personen/Fachbereiche/kommunale Gesellschaften für alle Maßnahmen"
        " hinterlegt?",
        default=False,
    )
    annual_reduction_of_emissions_can_be_predicted = models.BooleanField(
        "Wird anhand der Maßnahmen ein jährlicher Reduktionspfad des Energiebedarfs und der"
        " THG-Emissionen ersichtlich?",
        default=False,
    )
    concept_for_participation_specified = models.BooleanField(
        "Gibt es ein gutes Konzept zur Akteur:innenbeteiligung?",
        default=False,
    )
    sustainability_architecture_in_administration_exists = models.BooleanField(
        "Gibt es eine gute Nachhaltigkeitsarchitektur in der Verwaltung?",
        default=False,
    )
    climate_council_exists = models.BooleanField(
        "Gibt es einen Klimabeirat/Klimarat/Bürger:innenrat?", default=False
    )


class AdministrationChecklist(models.Model):
    class Meta:
        verbose_name = "Verwaltungsstrukturen Checkliste"

    city = models.OneToOneField(
        City,
        models.PROTECT,
        related_name="administration_checklist",
    )

    climate_protection_management_exists = models.BooleanField(
        "Gibt es ein Klimaschutzmanagement? Ist dieses befugt, Entscheidungen zu treffen? Sind"
        " Haushaltsmittel hinterlegt?",
        default=False,
    )
    climate_technical_committee_exists = models.BooleanField(
        "Gibt es einen Fachausschuss mit dem Fokus auf Klimaschutz? Ist dieser befugt,"
        " Haushaltsentscheidungen zu treffen?",
        default=False,
    )
    climate_relevance_check_exists = models.BooleanField(
        "Klimarelevanzprüfung: werden alle Beschlüsse von Verwaltung und Politik auf die"
        " Auswirkungen auf das Klima geprüft?",
        default=False,
    )
    interdisciplinary_climate_protection_exists = models.BooleanField(
        "Ist Klimaschutz als Querschnittsaufgabe über alle Fachbereiche etabliert?",
        default=False,
    )
    climate_protection_monitoring_exists = models.BooleanField(
        "Gibt es ein Monitoring von Kimaschutzmaßnahmen?",
        default=False,
    )
    intersectoral_concepts_exists = models.BooleanField(
        "Gibt es (sektorenübergreifende) Konzepte (siehe Planung und Konzepte bzw."
        " Sektorenübergreifende Konzepte)?",
        default=False,
    )
    climate_protection_reports_are_continuously_published = models.BooleanField(
        "Werden regelmäßige Klimaschutz- und Energieberichte veröffentlicht?",
        default=False,
    )
    guidelines_for_sustainable_procurement_exists = models.BooleanField(
        "Gibt es Richtlinien für ein nachhaltiges Beschaffungswesen?", default=False
    )
    municipal_office_for_funding_management_exists = models.BooleanField(
        "Gibt es eine eigene Kommunale Stelle für Fördermittelmanagement (unter anderem Beantragung"
        " etc. für den Klimaschutz)?",
        default=False,
    )
    public_relation_with_local_actors_exists = models.BooleanField(
        "Vernetzung in der Öffentlichkeitsarbeit mit lokalen Akteuren (Handwerk, Sparkasse...)?",
        default=False,
    )


class ExecutionStatus(models.IntegerChoices):
    UNKNOWN = 0, "unbekannt"
    AS_PLANNED = 2, "in Arbeit"
    COMPLETE = 4, "abgeschlossen"
    DELAYED = 6, "verzögert / fehlt"
    FAILED = 8, "gescheitert"


TASK_UNIQUE_CONSTRAINT_NAME = "unique_urls"


class Task(MP_Node):
    class Meta:
        verbose_name = "Sektor / Maßnahme"
        verbose_name_plural = "Sektoren und Maßnahmen"
        constraints = [
            models.UniqueConstraint(
                models.F("city"),
                models.F("slugs"),
                name=TASK_UNIQUE_CONSTRAINT_NAME,
            )
        ]

    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
    )

    draft_mode = models.BooleanField(
        "Entwurfs-Modus",
        default=True,
        help_text=(
            "Im Entwurfs-Modus wird ist der Sektor/die Maßnahme für normale Besucher im Frontend unsichtbar."
            " Nur wenn im gleichen Browser ein User im Admin angemeldet ist, wird er/sie angezeigt."
        ),
    )

    title = models.CharField(
        "Titel",
        max_length=255,
        help_text="""
            <p>Überschrift des Sektors, der Maßnahmengruppe oder der Maßnahme.</p>
            <p>Möglichst wie im Klimaaktionsplan angegeben.</p>
        """,
    )

    summary = models.TextField(
        "Kurztext",
        blank=True,
        help_text="""
            <p>Kann Beschreibung, Bewertung und Umsetzungsstand enthalten.</p>
            <p>Kann in einer Übersicht mehrerer Sektoren / Maßnahmen dargestellt werden.</p>
            <p>Deswegen möglichst kurz und ohne Formatierungen. Fett, Kursiv, Links, etc. sind okay.</p>
        """,
    )

    # 1. Beschreibung: Inhalte aus dem KAP

    description = models.TextField(
        "Beschreibung",
        blank=True,
        help_text="""
            <p>Texte aus dem Klimaaktionsplan können hier eins-zu-eins eingegeben werden.</p>
            <p>Für Sektoren und Maßnahmengruppen sind Einleitungstexte aus dem Plan geeignet.</p>
            <p>Für Maßnahmen sollte hier die genaue Beschreibung stehen.</p>
        """,
    )

    planned_start = models.DateField(
        "Geplanter Start",
        blank=True,
        null=True,
        help_text="Nur falls im Klimaaktionsplan angegeben.",
    )

    planned_completion = models.DateField(
        "Geplantes Ende",
        blank=True,
        null=True,
        help_text="Nur falls im Klimaaktionsplan angegeben.",
    )

    responsible_organ = models.TextField(
        "Verantwortliches Organ",
        blank=True,
        help_text="""
            <p>Genauer Name des verantwortlichen Gremiums oder der verantwortlichen Behörde.</p>
            <p>Möglichst mit Ansprechperson, Kontaktdaten und was sonst notwendig ist, um Informationen einzuholen.</p>
            <p>Diese Informationen könnten später in separate Felder aufgeteilt werden.</p>
        """,
    )

    # 2. Bewertung der KAP Inhalte

    plan_assessment = models.TextField(
        "Bewertung der Planung",
        blank=True,
        help_text="""
            <p>Würde(n) die im Klimaaktionsplan beschriebenen Maßnahme(n) ausreichen, um das gesteckte Ziel zu erreichen?</p>
            <p>Sollte das gesteckte Ziel nicht ausreichen, kann das auch hier beschrieben werden.</p>
        """,
    )

    # 3. Umsetzungsstand

    execution_status = models.IntegerField(
        "Umsetzungsstand",
        choices=ExecutionStatus.choices,
        default=ExecutionStatus.UNKNOWN,
        help_text="""
            <p>Bei Maßnahmen: Wird/wurde die Maßnahme wie geplant umgesetzt?</p>
            <dl>
                <dt>unbekannt</dt><dd><ul>
                    <li>Keine Infos vorhanden</li>
                    <li>Es gibt einen unkonkreten Beschluss</li>
                </ul></dd>
                <dt>in Arbeit</dt><dd><ul>
                    <li>Finden wir erstmal gut: Dinge werden bearbeitet.</li>
                    <li>Maßnahmen, die im Zeitplan sind (sowohl begonnen als auch in Planung).</li>
                    <li>Maßnahmen die in Umsetzung sind.</li>
                    <li>Maßnahmen für die es einen positiven Beschluss + Zeitplan (Konkretisierung) gibt.</li>
                </ul></dd>
                <dt>abgeschlossen</dt><dd><ul>
                    <li>Top und im Plan fertig.</li>
                </ul></dd>
                <dt>verzögert / fehlt</dt><dd><ul>
                    <li>Maßnahmen, die nicht im Zeitplan sind.</li>
                    <li>Maßnahmen, die im Prinzip noch vervollständigt werden können.</li>
                    <li>Maßnahmen, die im KAP nicht aufgeführt sind, (und nicht bearbeitet weden)</li>
                    <li>Im Prinzip könnten sie aber noch angegangen werden.</li>
                </ul></dd>
                <dt>gescheitert</dt><dd><ul>
                    <li>Kann niemals mehr geschafft werden (Eiche ist gefällt, Moor ist mit einer Autobahn überbaut)</li>
                    <li>Sowohl für Maßnahmen aus dem KAP, als auch Dinge, die gar nich im KAP aufgeführt waren.</li>
                </ul></dd>
            </dl>
            <p>Bei Sektoren / Maßnahmengruppen:</p>
            <p>Wenn hier "unbekannt" ausgewählt wird, werden die Umsetzungsstände der Maßnahmen in diesem Sektor / dieser Gruppe zusammengefasst.</p>
            <p>Bei anderen Auswahlen wird diese Zusammenfassung überschrieben. Das sollte nur passieren, wenn sie unpassend oder irreführend ist.</p>
        """,
    )

    execution_justification = models.TextField(
        "Begründung Umsetzungsstand",
        blank=True,
        help_text="Die Auswahl bei Umsetzungsstand kann hier ausführlich begründet werden.",
    )

    execution_completion = models.IntegerField(
        "Vervollständigungsgrad in Prozent",
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="""
            <p>Bei wenigen Maßnahmen ist es möglich den Fortschritt quantitativ einzugeben. Nur bei solchen sollte hier ein Wert eingegeben werden.</p>
            <p>Ob und wie diese Zahlen angezeigt werden, ist noch unklar.</p>
        """,
    )

    actual_start = models.DateField(
        "Tatsächlicher Start",
        blank=True,
        null=True,
        help_text="Nur falls bekannt.",
    )

    actual_completion = models.DateField(
        "Tatsächlicher Ende",
        blank=True,
        null=True,
        help_text="Nur falls bekannt.",
    )

    def __str__(self) -> str:
        return self.title

    slugs = models.SlugField(
        "In der URL",
        max_length=255,
        editable=False,
    )

    @staticmethod
    def _get_slugs_with_parent(new_parent, title):
        """Determine the `slugs` field based on the new parents slugs and title."""
        if new_parent:
            return new_parent.slugs + "/" + slugify(title)
        else:
            return slugify(title)

    @staticmethod
    def get_slugs_for_move(ref_node, pos, title):
        """Determine the `slugs` field given treebeards reference data.

        Some values of `pos` mean a position as sibling of ref_node and others
        as child. The latter all end with "-child".
        """
        if ref_node and isinstance(pos, str) and not pos.endswith("-child"):
            new_parent = ref_node.get_parent()
        else:
            new_parent = ref_node
        return Task._get_slugs_with_parent(new_parent, title)

    def validate_constraints(self, exclude=None):
        """
        Add slugs to fields to validate uniqueness and convert to a more readable error.

        This is necessary, because `editable=False` excludes the field from validation
        and UniqueConstraint does not allow error messages showing content.
        """

        if exclude:
            if "slugs" in exclude:
                exclude.remove("slugs")
            if "city" in exclude:
                exclude.remove("city")
        try:
            super().validate_constraints(exclude=exclude)
        except ValidationError as e:
            new_msg = (
                "Der Sektor / die Maßnahme wird in der URL als '%(slugs)s' geschrieben."
                " Das kollidiert mit einem anderen Eintrag." % {"slugs": self.slugs}
            )
            msgs: dict[str, str] = e.message_dict
            msgs[NON_FIELD_ERRORS][:] = [
                new_msg if TASK_UNIQUE_CONSTRAINT_NAME in msg else msg
                for msg in msgs[NON_FIELD_ERRORS]
            ]
            raise ValidationError(msgs)

    def move(self, target, pos=None):
        """Override to validate uniqueness of slugs field in case of move in changelist.

        It might also be possible to override `treebeard.admin.TreeAdmin.try_to_move_node()`,
        instead. This would possibly catch more cases.
        """

        self.slugs = self.get_slugs_for_move(target, pos, self.title)
        try:
            self.validate_constraints()
        except ValidationError as e:
            raise InvalidPosition(
                "Diese Verschiebung ist nicht möglich."
                " Es gibt bereits einen Sektor / eine Maßnahme"
                " mit der URL '%s'." % self.slugs
            )
        super().move(target, pos)

    def save(self, *args, **kwargs):
        """Override to correct `slugs` of whole sub-tree after move or rename.

        Calls itself recursively for all descendants after the regular save.

        Any move within the tree structure has to happen before such that
        `get_parent()` returns the correct parent. Treebeard first moves, then saves.
        """

        self.slugs = self._get_slugs_with_parent(self.get_parent(), self.title)
        super().save(*args, **kwargs)
        for child in self.get_children().only("slugs", "title"):
            child.save()

    def get_execution_status_name(self):
        for s in ExecutionStatus:
            if s.value == self.execution_status:
                return s.name
        return ""

    @property
    def started_late(self):
        return (
            self.planned_start
            and self.actual_start
            and self.planned_start < self.actual_start
        )

    @property
    def completed_late(self):
        return self.planned_completion and (
            not self.actual_completion
            and self.planned_completion < date.today()
            or self.actual_completion
            and self.planned_completion < self.actual_completion
        )

    # Maybe later. Not part of the MVP:

    # class Severities(models.IntegerChoices):
    #     CRITICAL = 5
    #     HIGH = 4
    #     STANDARD = 3
    #     LOW = 2
    #     VERY_LOW = 1
    # severity = models.IntegerField(
    #     "Schweregrad",
    #     choices=Severities.choices,
    #     default=Severities.STANDARD)

    # weight = models.IntegerField(
    #     "Gewicht",
    #     default=0,
    #     validators=[
    #         MinValueValidator(0),
    #         MaxValueValidator(3)
    #     ]
    # )


class Chart(models.Model):
    class Meta:
        verbose_name = "Diagramm"
        verbose_name_plural = "Diagramme"

    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="charts")
    image = models.ImageField("Bilddatei", upload_to="uploads/%Y/%m/%d/")
    alt_description = models.CharField(
        "Beschreibung (für Menschen, die das Bild nicht sehen können)", max_length=255
    )
    source = models.CharField("Quelle", max_length=255)
    license = models.CharField("Lizenz", max_length=255)
    caption = models.TextField("Bildunterschrift")

    def __str__(self) -> str:
        return self.alt_description + " - Quelle: " + self.source


# Tables for comparing and connecting the plans of all cities
# Lookup-entities (shared among all cities, entered by admins)

# This is currently kept out of the above city-specific data, since
# it might not be part of the MVP.

# Thoughts:
# - It might be better placed in a separate Django app, to keep it apart from the city stuff in the admin interface.
# - Sector / TaskCategory might be one table with recursive reference. Lets see, how that works out with the Tasks table.

# class Sector(models.Model):
#     name = models.CharField(max_length=100, unique=True)
#     ord = models.IntegerField(unique=True)

#     def __str__(self) -> str:
#         return self.name


# class TaskCategory(models.Model):
#     sector = models.ForeignKey(Sector, on_delete=models.PROTECT)
#     name = models.CharField(max_length=200, unique=True)
#     info = models.TextField()
#     ord = models.IntegerField(unique=True)

#     def __str__(self) -> str:
#         return self.name


# class TaskToCategory(models.Model):
#     task = models.ForeignKey(Task, on_delete=models.PROTECT)
#     category = models.ForeignKey(TaskCategory, on_delete=models.PROTECT)

#     def __str__(self) -> str:
#         return self.category.name + " - " + self.task.title
