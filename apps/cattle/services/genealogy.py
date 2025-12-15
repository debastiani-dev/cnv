from django.db.models import Avg, Count, Q

from apps.cattle.models import Cattle


class GenealogyService:
    @staticmethod
    def get_full_pedigree(root_animal):
        """
        Fetches the full ancestral tree using iterative batch fetching.
        Returns a nested dictionary structure representing the tree.
        """
        if not root_animal:
            return None

        # 1. Fetch all ancestors layer by layer
        # nodes_by_id: Maps ID -> Cattle Object
        nodes_by_id = {root_animal.pk: root_animal}

        # current_layer_ids: IDs of animals whose parents we need to fetch
        current_layer_ids = {root_animal.pk}

        # visited_ids: To prevent cycles (though model forbids self-parenting, loops could exist)
        visited_ids = {root_animal.pk}

        while current_layer_ids:
            # Fetch parents of the current layer
            parents = Cattle.objects.filter(
                Q(offspring_sire__pk__in=current_layer_ids)
                | Q(offspring_dam__pk__in=current_layer_ids)
            ).only(
                "uuid",
                "tag",
                "name",
                "sex",
                "image",
                "sire",
                "dam",
                "sire_external_id",
                "dam_external_id",
            )

            next_layer_ids = set()
            new_parents_found = False

            for parent in parents:
                if parent.pk not in visited_ids:
                    nodes_by_id[parent.pk] = parent
                    visited_ids.add(parent.pk)
                    next_layer_ids.add(parent.pk)
                    new_parents_found = True

            if not new_parents_found:
                break

            current_layer_ids = next_layer_ids

        # 2. Reconstruct the tree structure recursively from the flat map
        return GenealogyService._build_tree_node(root_animal, nodes_by_id)

    @staticmethod
    def _build_tree_node(animal, nodes_by_id, visited_path=None):
        """
        Helper to build a nested dictionary node from the flat map.
        visited_path ensures we don't recurse infinitely if there is a cycle in the map.
        """
        if visited_path is None:
            visited_path = set()

        if animal.pk in visited_path:
            return {"animal": animal, "sire": None, "dam": None, "is_cycle": True}

        visited_path.add(animal.pk)

        node = {"animal": animal, "sire": None, "dam": None}

        # Resolve Sire
        if animal.sire_id and animal.sire_id in nodes_by_id:
            sire_obj = nodes_by_id[animal.sire_id]
            node["sire"] = GenealogyService._build_tree_node(
                sire_obj, nodes_by_id, visited_path.copy()
            )
        elif animal.sire_external_id:
            # Placeholder for external parent (no recursive lookup possible)
            node["sire"] = {
                "external_name": animal.sire_external_id,
                "sex": Cattle.SEX_MALE,
            }

        # Resolve Dam
        if animal.dam_id and animal.dam_id in nodes_by_id:
            dam_obj = nodes_by_id[animal.dam_id]
            node["dam"] = GenealogyService._build_tree_node(
                dam_obj, nodes_by_id, visited_path.copy()
            )
        elif animal.dam_external_id:
            # Placeholder for external parent
            node["dam"] = {
                "external_name": animal.dam_external_id,
                "sex": Cattle.SEX_FEMALE,
            }

        return node

    @staticmethod
    def get_progeny_stats(animal):
        """
        Aggregates statistics for all direct children of the animal.
        """
        offspring = Cattle.objects.filter(Q(sire=animal) | Q(dam=animal))

        total_count = offspring.count()
        if total_count == 0:
            return {
                "total_offspring": 0,
                "avg_birth_weight": None,
                "avg_current_weight": None,
                "sex_distribution": [],
            }

        aggregates = offspring.aggregate(
            avg_birth_weight=Avg("weight_kg"), avg_current_weight=Avg("current_weight")
        )

        sex_distribution = list(
            offspring.values("sex").annotate(count=Count("sex")).order_by("sex")
        )

        # Map sex codes to labels if needed, or handle in template.
        # For API consistency, let's keep it raw or user-friendly? Raw is fine for template.

        return {
            "total_offspring": total_count,
            "avg_birth_weight": aggregates["avg_birth_weight"],
            "avg_current_weight": aggregates["avg_current_weight"],
            "sex_distribution": sex_distribution,
        }
